from payroll import payroll_results
import models

def test_tax():
    assert payroll_results["net_paye"] == 172831.35