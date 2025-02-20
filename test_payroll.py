from payroll import payroll_results

def test_tax():
    assert payroll_results["net_paye"] == 172831.35