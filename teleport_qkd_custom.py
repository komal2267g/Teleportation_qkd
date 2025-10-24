# teleport_qkd_custom.py
# Teleportation-based BB84 Quantum Key Distribution (QKD) Simulation in Qiskit 2.x
# Compatible with Python 3.13 + Qiskit 2.1.1 + Qiskit Aer 0.17.2

import random
import numpy as np
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from qiskit_aer import AerSimulator
import matplotlib.pyplot as plt

# ---------------- CONFIG ----------------
_DEBUG_CIRCUIT = True
backend = AerSimulator()
# ----------------------------------------

def prepare_bb84_state(qc, q, bit, basis):
    """Prepare BB84 state |0>, |1>, |+>, or |->"""
    if basis == 'Z':
        if bit == 1:
            qc.x(q)
    elif basis == 'X':
        if bit == 0:
            qc.h(q)
        else:
            qc.x(q)
            qc.h(q)

def bell_pair(qc, a, b):
    qc.h(a)
    qc.cx(a, b)

def run_single_round(alice_bit, alice_basis, bob_basis, use_eve=False):
    """Run one teleportation-based BB84 round."""
    qr = QuantumRegister(3, 'q')
    cr = ClassicalRegister(3, 'c')
    qc = QuantumCircuit(qr, cr)

    # Step 1: Create Bell pair between q1 (Alice) and q2 (Bob)
    bell_pair(qc, qr[1], qr[2])

    # Optional Eve attack
    if use_eve and random.random() < 0.5:
        eve_basis = random.choice(['Z', 'X'])
        if eve_basis == 'X':
            qc.h(qr[1])
        qc.measure(qr[1], cr[0])
        if eve_basis == 'X':
            qc.h(qr[1])

    # Step 2: Alice prepares her qubit
    prepare_bb84_state(qc, qr[0], alice_bit, alice_basis)

    # Step 3: Alice performs Bell measurement
    qc.cx(qr[0], qr[1])
    qc.h(qr[0])
    qc.measure(qr[0], cr[0])
    qc.measure(qr[1], cr[1])

    # Step 4: Bob’s corrections
    qc.cx(qr[1], qr[2])
    qc.cz(qr[0], qr[2])

    # Step 5: Bob measures in chosen basis
    if bob_basis == 'X':
        qc.h(qr[2])
    qc.measure(qr[2], cr[2])

    # Draw and save one example circuit
    global _DEBUG_CIRCUIT
    if _DEBUG_CIRCUIT:
        print("\n--- Example Circuit ---")
        print(qc.draw(output='text'))
        qc.draw(output='mpl', filename='example_circuit.png')
        plt.show()
        _DEBUG_CIRCUIT = False

    # Execute circuit
    job = backend.run(transpile(qc, backend), shots=1)
    result = job.result().get_counts()

    key = max(result, key=result.get)
    key = key.replace(' ', '')  # remove spaces like '100 1' → '1001'
    measured_bit = int(key[-1])  # Bob's measurement (last bit)

    return alice_bit, alice_basis, bob_basis, measured_bit

def run_protocol(num_rounds, use_eve=False, custom_inputs=None):
    alice_bits, alice_bases, bob_bases, bob_results = [], [], [], []

    for i in range(num_rounds):
        if custom_inputs:
            a_bit = custom_inputs['alice_bits'][i]
            a_basis = custom_inputs['alice_bases'][i]
            b_basis = custom_inputs['bob_bases'][i]
        else:
            a_bit = random.choice([0, 1])
            a_basis = random.choice(['Z', 'X'])
            b_basis = random.choice(['Z', 'X'])

        _, _, _, b_meas = run_single_round(a_bit, a_basis, b_basis, use_eve)
        alice_bits.append(a_bit)
        alice_bases.append(a_basis)
        bob_bases.append(b_basis)
        bob_results.append(b_meas)

    # Sifting step
    sifted_alice, sifted_bob = [], []
    for a_b, a_k, b_b, b_m in zip(alice_bases, alice_bits, bob_bases, bob_results):
        if a_b == b_b:
            sifted_alice.append(a_k)
            sifted_bob.append(b_m)

    if len(sifted_alice) == 0:
        qber = None
    else:
        errors = sum(1 for x, y in zip(sifted_alice, sifted_bob) if x != y)
        qber = errors / len(sifted_alice)

    return {
        'raw_rounds': num_rounds,
        'sifted_length': len(sifted_alice),
        'qber': qber,
        'alice_bits': alice_bits,
        'bob_results': bob_results,
        'alice_bases': alice_bases,
        'bob_bases': bob_bases,
        'sifted_alice': sifted_alice,
        'sifted_bob': sifted_bob
    }

# ---------------- MAIN ----------------
if __name__ == "__main__":
    print("Teleportation-based BB84 Quantum Key Distribution Simulation\n")

    use_custom = input("Do you want to provide custom inputs? (y/n): ").strip().lower()
    custom_inputs = None

    if use_custom == 'y':
        n = int(input("Enter number of bits (e.g. 4): "))
        bits = list(map(int, input(f"Enter {n} bits (0/1) for Alice, separated by spaces: ").split()))
        a_bases = input(f"Enter {n} bases (Z/X) for Alice, separated by spaces: ").split()
        b_bases = input(f"Enter {n} bases (Z/X) for Bob, separated by spaces: ").split()

        custom_inputs = {
            'alice_bits': bits,
            'alice_bases': a_bases,
            'bob_bases': b_bases
        }
        num_rounds = n
    else:
        num_rounds = 8  # default

    print("\nRunning teleportation-based BB84 (honest)...")
    honest = run_protocol(num_rounds, use_eve=False, custom_inputs=custom_inputs)
    print(f"Honest -> rounds: {honest['raw_rounds']}, sifted: {honest['sifted_length']}, QBER: {honest['qber']:.3f}")

    print("\nRunning teleportation-based BB84 (Eve intercept-resend)...")
    eve = run_protocol(num_rounds, use_eve=True, custom_inputs=custom_inputs)
    print(f"Eve -> rounds: {eve['raw_rounds']}, sifted: {eve['sifted_length']}, QBER: {eve['qber']:.3f}")

    print("\nExample Results (Honest):")
    print("Alice bits :", honest['alice_bits'])
    print("Alice bases:", honest['alice_bases'])
    print("Bob bases  :", honest['bob_bases'])
    print("Bob results:", honest['bob_results'])
    print("Sifted key (same bases):")
    print("Alice:", honest['sifted_alice'])
    print("Bob  :", honest['sifted_bob'])