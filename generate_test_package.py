"""
generate_test_package.py

Generates realistic mock borrower documents (images & PDFs) to test the 
complete AI Loan Processing Pipeline, including:
  1. Standard Clean Approval Package (PAN, Payslip, Bank Statement, Aadhaar)
  2. Mismatched Identity Package (triggers IDENTITY_MISMATCH)
  3. Income Discrepancy & High DTI Package (triggers INCOME_DISCREPANCY & HIGH_DTI)
  4. Incomplete Package (triggers INCOMPLETE missing documents warning)
"""

import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import fitz  # PyMuPDF


TEST_DIR = Path("test_documents")
TEST_DIR.mkdir(exist_ok=True)


def get_font(size=14, bold=False):
    """Attempts to load a standard system font; falls back to default if unavailable."""
    font_names = ["arialbd.ttf" if bold else "arial.ttf", "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"]
    for font_name in font_names:
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    return ImageFont.load_default()


# =====================================================================
# 1. Image Document Generators (PAN, Aadhaar)
# =====================================================================

def generate_pan_card(filename: str, name: str = "SHASHANK DATTU", pan: str = "ABCDE1234F", dob: str = "1998-05-15"):
    """Generates a synthetic PAN Card graphic."""
    img = Image.new("RGB", (650, 400), color="#E8F4F8")
    draw = ImageDraw.Draw(img)

    # Header & Border
    draw.rectangle([10, 10, 640, 390], outline="#1A5276", width=3)
    draw.rectangle([10, 10, 640, 65], fill="#1A5276")
    
    title_font = get_font(20, bold=True)
    draw.text((160, 20), "INCOME TAX DEPARTMENT", fill="white", font=title_font)
    draw.text((220, 45), "GOVT. OF INDIA", fill="#FAD7A0", font=get_font(12, bold=True))

    # Details
    lbl_font = get_font(12, bold=False)
    val_font = get_font(15, bold=True)

    draw.text((40, 90), "Permanent Account Number (PAN):", fill="#555555", font=lbl_font)
    draw.text((40, 110), pan, fill="#900C3F", font=get_font(22, bold=True))

    draw.text((40, 160), "Name / Legal Name:", fill="#555555", font=lbl_font)
    draw.text((40, 180), name, fill="#000000", font=val_font)

    draw.text((40, 230), "Father's Name:", fill="#555555", font=lbl_font)
    draw.text((40, 250), "RAMESH DATTU", fill="#000000", font=val_font)

    draw.text((40, 300), "Date of Birth (YYYY-MM-DD):", fill="#555555", font=lbl_font)
    draw.text((40, 320), dob, fill="#000000", font=val_font)

    # Photo Box Placeholder
    draw.rectangle([480, 110, 600, 260], fill="#D5D8DC", outline="#7F8C8D", width=2)
    draw.text((515, 175), "PHOTO", fill="#566573", font=lbl_font)

    filepath = TEST_DIR / filename
    img.save(filepath)
    print(f"Generated: {filepath}")
    return filepath


def generate_aadhaar_card(filename: str, name: str = "SHASHANK DATTU", dob: str = "1998-05-15", last4: str = "7890"):
    """Generates a synthetic Aadhaar Identity Proof graphic."""
    img = Image.new("RGB", (650, 400), color="#FFFFFF")
    draw = ImageDraw.Draw(img)

    # Header Bar
    draw.rectangle([10, 10, 640, 390], outline="#D35400", width=3)
    draw.rectangle([10, 10, 640, 60], fill="#E67E22")
    draw.text((140, 22), "UNIQUE IDENTIFICATION AUTHORITY OF INDIA", fill="white", font=get_font(16, bold=True))

    lbl_font = get_font(12, bold=False)
    val_font = get_font(15, bold=True)

    # Photo Placeholder
    draw.rectangle([40, 90, 170, 240], fill="#E5E8E8", outline="#BDC3C7", width=2)
    draw.text((80, 155), "PHOTO", fill="#7F8C8D", font=lbl_font)

    draw.text((200, 100), "Name:", fill="#555555", font=lbl_font)
    draw.text((200, 120), name, fill="#000000", font=val_font)

    draw.text((200, 160), "DOB:", fill="#555555", font=lbl_font)
    draw.text((200, 180), dob, fill="#000000", font=val_font)

    draw.text((200, 220), "Gender:", fill="#555555", font=lbl_font)
    draw.text((200, 240), "Male", fill="#000000", font=val_font)

    # Aadhaar Number
    draw.rectangle([30, 310, 620, 365], fill="#FEF9E7")
    draw.text((170, 325), f"XXXX XXXX {last4}", fill="#900C3F", font=get_font(22, bold=True))

    filepath = TEST_DIR / filename
    img.save(filepath)
    print(f"Generated: {filepath}")
    return filepath


# =====================================================================
# 2. PDF Document Generators (Payslip, Bank Statement, Form 16)
# =====================================================================

def generate_payslip_pdf(
    filename: str,
    employee_name: str = "SHASHANK DATTU",
    employer_name: str = "TechHive Solutions Pvt Ltd",
    gross_pay: float = 95000.0,
    deductions: float = 10000.0,
    pay_month: str = "2026-07"
):
    """Generates a structured Salary Slip PDF."""
    net_pay = gross_pay - deductions
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 size

    # Header
    page.draw_rect(fitz.Rect(30, 30, 565, 85), color=(0.1, 0.3, 0.5), fill=(0.95, 0.97, 1.0))
    page.insert_text((45, 55), employer_name.upper(), fontsize=16, fontname="helv", color=(0.1, 0.3, 0.5))
    page.insert_text((45, 75), f"SALARY SLIP FOR THE MONTH OF: {pay_month}", fontsize=11, fontname="helv")

    # Employee Information
    y = 120
    page.insert_text((45, y), f"Employee Name : {employee_name}", fontsize=11, fontname="helv")
    page.insert_text((330, y), f"Designation   : Senior Software Engineer", fontsize=11, fontname="helv")
    y += 20
    page.insert_text((45, y), "Bank Account  : HDFC Bank - ****4412", fontsize=11, fontname="helv")
    page.insert_text((330, y), "Pay Cycle     : Monthly", fontsize=11, fontname="helv")

    # Earnings & Deductions Table
    y = 170
    page.draw_rect(fitz.Rect(40, y, 555, y + 25), fill=(0.2, 0.4, 0.6))
    page.insert_text((50, y + 17), "EARNINGS", fontsize=11, fontname="helv", color=(1, 1, 1))
    page.insert_text((220, y + 17), "AMOUNT (₹)", fontsize=11, fontname="helv", color=(1, 1, 1))
    page.insert_text((310, y + 17), "DEDUCTIONS", fontsize=11, fontname="helv", color=(1, 1, 1))
    page.insert_text((470, y + 17), "AMOUNT (₹)", fontsize=11, fontname="helv", color=(1, 1, 1))

    # Line items
    y += 40
    basic = gross_pay * 0.50
    hra = gross_pay * 0.30
    special = gross_pay * 0.20
    pf = deductions * 0.60
    pt = 200.0
    tds = deductions - pf - pt

    items = [
        ("Basic Salary", f"{basic:,.2f}", "Provident Fund (PF)", f"{pf:,.2f}"),
        ("House Rent Allowance", f"{hra:,.2f}", "Professional Tax", f"{pt:,.2f}"),
        ("Special Allowance", f"{special:,.2f}", "Income Tax (TDS)", f"{tds:,.2f}"),
    ]

    for earn_lbl, earn_val, ded_lbl, ded_val in items:
        page.insert_text((50, y), earn_lbl, fontsize=10, fontname="helv")
        page.insert_text((220, y), earn_val, fontsize=10, fontname="helv")
        page.insert_text((310, y), ded_lbl, fontsize=10, fontname="helv")
        page.insert_text((470, y), ded_val, fontsize=10, fontname="helv")
        y += 25

    # Totals Row
    y += 15
    page.draw_rect(fitz.Rect(40, y, 555, y + 30), color=(0.7, 0.7, 0.7), fill=(0.95, 0.95, 0.95))
    page.insert_text((50, y + 20), f"Gross Earnings: ₹{gross_pay:,.2f}", fontsize=11, fontname="helv")
    page.insert_text((310, y + 20), f"Total Deductions: ₹{deductions:,.2f}", fontsize=11, fontname="helv")

    # Net Pay Callout
    y += 50
    page.draw_rect(fitz.Rect(40, y, 555, y + 45), fill=(0.1, 0.5, 0.2))
    page.insert_text((60, y + 28), f"NET TAKE-HOME SALARY : ₹{net_pay:,.2f}", fontsize=14, fontname="helv", color=(1, 1, 1))

    filepath = TEST_DIR / filename
    doc.save(filepath)
    doc.close()
    print(f"Generated: {filepath}")
    return filepath


def generate_bank_statement_pdf(
    filename: str,
    account_holder: str = "SHASHANK DATTU",
    salary_amount: float = 85000.0,
    emi_amount: float = 18000.0,
    opening_bal: float = 45000.0
):
    """Generates a multi-transaction Bank Statement PDF with classified salary credits and EMI debits."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # Bank Header
    page.draw_rect(fitz.Rect(30, 30, 565, 80), fill=(0.05, 0.2, 0.45))
    page.insert_text((45, 58), "HDFC BANK LIMITED — STATEMENT OF ACCOUNT", fontsize=14, fontname="helv", color=(1, 1, 1))

    y = 105
    page.insert_text((45, y), f"Account Holder : {account_holder}", fontsize=10, fontname="helv")
    page.insert_text((340, y), "Account Number : 5010049284412", fontsize=10, fontname="helv")
    y += 18
    page.insert_text((45, y), "Statement Period : 01-Jul-2026 to 31-Jul-2026", fontsize=10, fontname="helv")
    page.insert_text((340, y), "Branch         : Pune Main Branch", fontsize=10, fontname="helv")

    # Balance Summary
    y += 30
    page.draw_rect(fitz.Rect(40, y, 555, y + 25), fill=(0.9, 0.92, 0.95))
    page.insert_text((50, y + 17), f"Opening Balance: ₹{opening_bal:,.2f}", fontsize=10, fontname="helv")

    # Transactions Table Header
    y += 40
    page.draw_rect(fitz.Rect(40, y, 555, y + 20), fill=(0.2, 0.2, 0.2))
    page.insert_text((45, y + 14), "Date", fontsize=9, fontname="helv", color=(1, 1, 1))
    page.insert_text((120, y + 14), "Transaction Narration", fontsize=9, fontname="helv", color=(1, 1, 1))
    page.insert_text((340, y + 14), "Type", fontsize=9, fontname="helv", color=(1, 1, 1))
    page.insert_text((400, y + 14), "Amount (₹)", fontsize=9, fontname="helv", color=(1, 1, 1))
    page.insert_text((480, y + 14), "Balance (₹)", fontsize=9, fontname="helv", color=(1, 1, 1))

    # Transactions List
    running_bal = opening_bal
    txs = [
        ("01-Jul-2026", "ACH CR - SALARY TechHive Solutions", "CREDIT", salary_amount),
        ("05-Jul-2026", "ACH DR - HDFC AUTO LOAN EMI", "DEBIT", emi_amount),
        ("10-Jul-2026", "UPI/Swiggy/FoodOrder/9941", "DEBIT", 850.0),
        ("15-Jul-2026", "UPI/AmazonPay/Shopping/3312", "DEBIT", 4500.0),
        ("20-Jul-2026", "ATM CASH WDL - PUNE BR", "DEBIT", 10000.0),
        ("28-Jul-2026", "ELECTRICITY BILL PAYMENT MSEB", "DEBIT", 2300.0)
    ]

    y += 30
    for t_date, desc, tx_type, amt in txs:
        if tx_type == "CREDIT":
            running_bal += amt
        else:
            running_bal -= amt

        page.insert_text((45, y), t_date, fontsize=9, fontname="helv")
        page.insert_text((120, y), desc[:35], fontsize=9, fontname="helv")
        page.insert_text((340, y), tx_type, fontsize=9, fontname="helv")
        page.insert_text((400, y), f"{amt:,.2f}", fontsize=9, fontname="helv")
        page.insert_text((480, y), f"{running_bal:,.2f}", fontsize=9, fontname="helv")
        y += 22

    # Closing Balance
    y += 20
    page.draw_rect(fitz.Rect(40, y, 555, y + 25), fill=(0.9, 0.95, 0.9))
    page.insert_text((50, y + 17), f"Closing Balance: ₹{running_bal:,.2f}", fontsize=10, fontname="helv")
    page.insert_text((300, y + 17), f"Total Monthly Salary Credit: ₹{salary_amount:,.2f}", fontsize=10, fontname="helv")

    filepath = TEST_DIR / filename
    doc.save(filepath)
    doc.close()
    print(f"Generated: {filepath}")
    return filepath


# =====================================================================
# 3. Test Suite Bundler
# =====================================================================

def generate_all_test_packages():
    """Generates a complete matrix of test document packages."""
    print("=" * 60)
    print("🛠️ Generating Test Document Suite for Loan Processor AI")
    print("=" * 60)

    # 1. Clean Approved Package
    generate_pan_card("pkg1_clean_pan.png", name="SHASHANK DATTU", pan="ABCDE1234F", dob="1998-05-15")
    generate_aadhaar_card("pkg1_clean_aadhaar.png", name="SHASHANK DATTU", dob="1998-05-15", last4="7890")
    generate_payslip_pdf("pkg1_clean_payslip.pdf", employee_name="SHASHANK DATTU", employer_name="TechHive Solutions Pvt Ltd", gross_pay=95000.0, deductions=10000.0)
    generate_bank_statement_pdf("pkg1_clean_bank_stmt.pdf", account_holder="SHASHANK DATTU", salary_amount=85000.0, emi_amount=15000.0)

    # 2. Identity Mismatch Package (Different name on Payslip and Bank Statement)
    generate_pan_card("pkg2_mismatch_pan.png", name="SHASHANK DATTU", pan="ABCDE1234F", dob="1998-05-15")
    generate_payslip_pdf("pkg2_mismatch_payslip.pdf", employee_name="VIKRAM ADITYA SINGH", employer_name="TechHive Solutions Pvt Ltd", gross_pay=95000.0, deductions=10000.0)
    generate_bank_statement_pdf("pkg2_mismatch_bank_stmt.pdf", account_holder="VIKRAM ADITYA SINGH", salary_amount=85000.0, emi_amount=15000.0)

    # 3. High DTI & Income Discrepancy Package (Low actual salary & High undisclosed EMI)
    generate_pan_card("pkg3_high_risk_pan.png", name="AMIT VERMA", pan="VERMA8877K", dob="1992-10-20")
    generate_payslip_pdf("pkg3_high_risk_payslip.pdf", employee_name="AMIT VERMA", employer_name="Apex Global Corp", gross_pay=40000.0, deductions=5000.0)
    generate_bank_statement_pdf("pkg3_high_risk_bank_stmt.pdf", account_holder="AMIT VERMA", salary_amount=35000.0, emi_amount=28000.0)  # DTI > 80%

    print("\n✅ All test suites successfully created inside the './test_documents/' directory!")


if __name__ == "__main__":
    generate_all_test_packages()