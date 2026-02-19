
# Valid Ranges
MIN_FREQ, MAX_FREQ = 28.0, 32.0
MIN_RPM, MAX_RPM = 1750, 1900
MIN_CUT_SEC, MAX_CUT_SEC = 15.0, 17.0
MIN_DEPTH_2ND, MAX_DEPTH_2ND = 0.02, 0.04
MIN_TENSION, MAX_TENSION = 2.5, 2.8

def check_ranges(freq, rpm, cut_sec, depth, tension):
    errors = []
    if not (MIN_FREQ <= freq <= MAX_FREQ):
        errors.append(f"Frequency {freq} out of range {MIN_FREQ}-{MAX_FREQ}")
    if not (MIN_RPM <= rpm <= MAX_RPM):
        errors.append(f"RPM {rpm} out of range {MIN_RPM}-{MAX_RPM}")
    if not (MIN_CUT_SEC <= cut_sec <= MAX_CUT_SEC):
        errors.append(f"Cut Sec {cut_sec} out of range {MIN_CUT_SEC}-{MAX_CUT_SEC}")
    if not (MIN_DEPTH_2ND <= depth <= MAX_DEPTH_2ND):
        errors.append(f"Depth {depth} out of range {MIN_DEPTH_2ND}-{MAX_DEPTH_2ND}")
    if not (MIN_TENSION <= tension <= MAX_TENSION):
        errors.append(f"Tension {tension} out of range {MIN_TENSION}-{MAX_TENSION}")
    return errors

# Test Cases
test_cases = [
    # Pass Case
    {"freq": 30.0, "rpm": 1860, "cut_sec": 16.0, "depth": 0.03, "tension": 2.7, "expected": "PASS"},
    # Boundary Pass Case (Low)
    {"freq": 28.0, "rpm": 1750, "cut_sec": 15.0, "depth": 0.02, "tension": 2.5, "expected": "PASS"},
    # Boundary Pass Case (High)
    {"freq": 32.0, "rpm": 1900, "cut_sec": 17.0, "depth": 0.04, "tension": 2.8, "expected": "PASS"},
    # Fail Case (Low)
    {"freq": 27.9, "rpm": 1749, "cut_sec": 14.9, "depth": 0.01, "tension": 2.4, "expected": "FAIL"},
    # Fail Case (High)
    {"freq": 32.1, "rpm": 1901, "cut_sec": 17.1, "depth": 0.05, "tension": 2.9, "expected": "FAIL"},
]

print("Running Logic Verification...")
all_passed = True
for i, test in enumerate(test_cases):
    errors = check_ranges(test["freq"], test["rpm"], test["cut_sec"], test["depth"], test["tension"])
    result = "PASS" if not errors else "FAIL"
    
    if result == test["expected"]:
        print(f"Test Case {i+1}: OK ({result})")
    else:
        print(f"Test Case {i+1}: FAILED (Expected {test['expected']}, Got {result})")
        print(f"Errors: {errors}")
        all_passed = False

if all_passed:
    print("\n✅ All validation logic tests passed.")
else:
    print("\n❌ Some tests failed.")
