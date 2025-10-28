#!/usr/bin/env python3
"""
Bill Splitter for Groups
Features:
 - Even split
 - Uneven split by percentages (validated to 100%)
 - Optional person names
 - Rounding to 2 decimal places (banker's/round-half-up via Decimal)
 - Input validation (non-negative amounts, non-zero people)
 - Multiple splits per session
 - Export results to a .txt file
"""

from decimal import Decimal, ROUND_HALF_UP, InvalidOperation, getcontext
import json
import time
import os

# Ensure enough precision
getcontext().prec = 28

def to_decimal(value_str):
    """Safely convert input string to Decimal, stripping currency symbols and commas."""
    try:
        cleaned = value_str.strip().replace(',', '').replace('$', '')
        d = Decimal(cleaned)
        return d
    except (InvalidOperation, ValueError):
        raise ValueError("Please enter a valid numeric amount.")

def round_money(amount):
    """Round a Decimal to 2 decimal places using ROUND_HALF_UP."""
    return amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

def get_positive_decimal(prompt):
    while True:
        s = input(prompt).strip()
        try:
            d = to_decimal(s)
            if d < 0:
                print("Amount cannot be negative. Try again.")
                continue
            return d
        except ValueError:
            print("Invalid number. Try again (e.g. 123.45).")

def get_positive_int(prompt, min_value=1):
    while True:
        s = input(prompt).strip()
        if not s.isdigit():
            print("Please enter a positive integer.")
            continue
        n = int(s)
        if n < min_value:
            print(f"Please enter an integer >= {min_value}.")
            continue
        return n

def ask_names(n):
    names = []
    use_names = input("Would you like to enter names for each person? (y/N): ").strip().lower()
    if use_names == 'y':
        for i in range(1, n+1):
            name = input(f"  Enter name for person #{i} (leave blank for default): ").strip()
            if not name:
                name = f"Person {i}"
            names.append(name)
    else:
        names = [f"Person {i}" for i in range(1, n+1)]
    return names

def split_evenly(total, n, names=None):
    """Return list of (name, amount) tuples for even split with 2-decimal rounding and adjusting remainder."""
    if names is None:
        names = [f"Person {i}" for i in range(1, n+1)]
    # base share (unrounded)
    base = total / Decimal(n)
    rounded_shares = [round_money(base) for _ in range(n)]
    # Adjust rounding residual so sum equals total
    sum_rounded = sum(rounded_shares)
    residual = total - sum_rounded
    # residual is typically small (like a few cents). Distribute one-cent increments.
    cent = Decimal('0.01')
    i = 0
    # Decide sign and direction
    while residual != Decimal('0.00'):
        if residual > Decimal('0.00'):
            rounded_shares[i] += cent
            residual -= cent
        else:
            rounded_shares[i] -= cent
            residual += cent
        i = (i + 1) % n
    return list(zip(names, rounded_shares))

def split_by_percentage(total, percentages, names=None):
    """percentages: list of Decimal percentages (e.g., Decimal('30') for 30%).
       Returns list of (name, amount)."""
    if names is None:
        names = [f"Person {i}" for i in range(1, len(percentages)+1)]
    # Convert percentages to decimals (e.g. 30 -> 0.30)
    shares = []
    for p in percentages:
        share = (p / Decimal('100')) * total
        shares.append(round_money(share))
    # Adjust rounding residual
    sum_shares = sum(shares)
    residual = total - sum_shares
    cent = Decimal('0.01')
    i = 0
    n = len(shares)
    while residual != Decimal('0.00'):
        if residual > Decimal('0.00'):
            shares[i] += cent
            residual -= cent
        else:
            shares[i] -= cent
            residual += cent
        i = (i + 1) % n
    return list(zip(names, shares))

def export_to_txt(filename, result_summary):
    """Writes the result_summary (string) to filename. Avoid overwriting by default."""
    base, ext = os.path.splitext(filename)
    if not ext:
        ext = '.txt'
    safe_filename = base + ext
    # If file exists, append timestamp to avoid accidental overwrite
    if os.path.exists(safe_filename):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        safe_filename = f"{base}_{timestamp}{ext}"
    with open(safe_filename, 'w', encoding='utf-8') as f:
        f.write(result_summary)
    return safe_filename

def format_result_header(total, method, n, names=None):
    lines = []
    lines.append("Bill Split Result")
    lines.append(f"Method: {method}")
    lines.append(f"Total amount: {total}")
    lines.append(f"Number of people: {n}")
    if names:
        lines.append("Names: " + ", ".join(names))
    lines.append("-" * 40)
    return "\n".join(lines) + "\n"

def run_single_split():
    # inputs
    total = get_positive_decimal("Enter total bill amount: ")
    n = get_positive_int("Enter number of people sharing the bill: ", min_value=1)
    names = ask_names(n)

    # choose method
    while True:
        method = input("Split method - Even (E) or By Percentage (P)? [E/P]: ").strip().lower()
        if method in ('e', 'p'):
            break
        print("Please enter 'E' for even or 'P' for percentage-based split.")

    if method == 'e':
        result = split_evenly(total, n, names)
        header = format_result_header(round_money(total), "Even", n, names)
    else:
        # collect percentages
        percentages = []
        print("Enter each person's contribution percentage (values should sum to 100).")
        for i in range(n):
            while True:
                p_input = input(f"  Percentage for {names[i]}: ").strip()
                try:
                    p = to_decimal(p_input)
                    if p < 0:
                        print("Percentage cannot be negative.")
                        continue
                    percentages.append(p)
                    break
                except ValueError:
                    print("Invalid percentage. Try again (e.g. 25 or 12.5).")
        # validate sum close to 100
        total_percent = sum(percentages)
        # allow a tiny tolerance (0.01) because of user decimals
        if not (Decimal('100') - Decimal('0.01') <= total_percent <= Decimal('100') + Decimal('0.01')):
            print(f"Percentages sum to {total_percent}%. They must sum to 100%. Please re-enter split.")
            return None  # caller will just continue session
        result = split_by_percentage(total, percentages, names)
        header = format_result_header(round_money(total), "By Percentage", n, names)

    # display results
    lines = [header]
    for name, amount in result:
        lines.append(f"{name}: {amount} ")
    lines.append("-" * 40)
    lines.append(f"Total: {sum(amount for _, amount in result)}")
    result_text = "\n".join(lines)
    print("\n" + result_text + "\n")

    # offer export
    save = input("Would you like to export results to a .txt file? (y/N): ").strip().lower()
    if save == 'y':
        default_name = f"bill_split_{time.strftime('%Y%m%d-%H%M%S')}.txt"
        filename = input(f"Enter filename (default '{default_name}'): ").strip()
        if not filename:
            filename = default_name
        saved = export_to_txt(filename, result_text)
        print(f"Saved to {saved}")
    return result_text

def main():
    print("=== Bill Splitter for Groups ===")
    session_history = []
    while True:
        res = run_single_split()
        if res is not None:
            session_history.append({
                'timestamp': time.time(),
                'result': res
            })
        cont = input("Do you want to perform another split? (Y/n): ").strip().lower()
        if cont == 'n':
            break
    # Optionally save session history in JSON
    save_hist = input("Save session history as JSON? (y/N): ").strip().lower()
    if save_hist == 'y' and session_history:
        filename = f"bill_split_history_{time.strftime('%Y%m%d-%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(session_history, f, indent=2, default=str)
        print(f"Session history saved as {filename}")

    print("Thanks for using Bill Splitter. Goodbye!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.")