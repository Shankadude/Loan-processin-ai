import io
import os
from PIL import Image, ImageDraw

def create_synthetic_pan(name: str, pan: str, dob: str) -> bytes:
    img = Image.new("RGB", (650, 380), color="#edf2f7")
    draw = ImageDraw.Draw(img)
    draw.rectangle([(10, 10), (640, 370)], outline="#2b6cb0", width=3)
    draw.text((30, 25), "INCOME TAX DEPARTMENT - GOVT. OF INDIA", fill="#1a365d")
    draw.text((30, 60), "Permanent Account Number Card", fill="#2d3748")
    draw.text((30, 130), f"Name: {name.upper()}", fill="#1a202c")
    draw.text((30, 180), f"Father's Name: SURESH {name.split()[-1].upper()}", fill="#1a202c")
    draw.text((30, 230), f"DOB: {dob}", fill="#1a202c")
    draw.text((30, 290), f"PAN: {pan}", fill="#2b6cb0")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def create_synthetic_payslip(name: str, employer: str, gross: float, net: float) -> bytes:
    img = Image.new("RGB", (700, 500), color="#ffffff")
    draw = ImageDraw.Draw(img)
    draw.rectangle([(15, 15), (685, 485)], outline="#4a5568", width=2)
    draw.text((40, 30), f"{employer.upper()} - SALARY STATEMENT", fill="#2d3748")
    draw.text((40, 60), "Pay Period: July 2026", fill="#718096")
    draw.line([(40, 90), (660, 90)], fill="#cbd5e0", width=2)
    
    draw.text((40, 120), f"Employee Name: {name}", fill="#1a202c")
    draw.text((40, 160), "Designation: Senior Software Engineer", fill="#1a202c")
    draw.text((40, 200), f"Gross Monthly Income: {gross:.2f}", fill="#1a202c")
    draw.text((40, 240), f"Total Deductions: {gross - net:.2f}", fill="#e53e3e")
    draw.text((40, 280), f"Net Take-Home Pay: {net:.2f}", fill="#2b6cb0")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def create_synthetic_bank_stmt(name: str, bank: str, credit: float, emi: float) -> bytes:
    img = Image.new("RGB", (700, 550), color="#f7fafc")
    draw = ImageDraw.Draw(img)
    draw.rectangle([(15, 15), (685, 535)], outline="#2c5282", width=2)
    draw.text((40, 30), f"{bank.upper()} - ACCOUNT STATEMENT", fill="#2b6cb0")
    draw.text((40, 65), f"Account Holder: {name}", fill="#1a202c")
    draw.text((40, 100), "Statement Period: 01/07/2026 to 31/07/2026", fill="#718096")
    draw.line([(40, 130), (660, 130)], fill="#cbd5e0", width=2)
    
    draw.text((40, 160), "Monthly Transaction Breakdown:", fill="#2d3748")
    draw.text((40, 200), f"• Total Monthly Salary Credits: {credit:.2f}", fill="#38a169")
    draw.text((40, 240), f"• Total Recurring Loan/EMI Debits: {emi:.2f}", fill="#e53e3e")
    draw.text((40, 280), "• Average Monthly Balance: 48000.00", fill="#1a202c")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def generate_all():
    os.makedirs("test_documents", exist_ok=True)
    
    name = "Shashank Dattu"
    pan_bytes = create_synthetic_pan(name, "ABCDE1234F", "15/08/1998")
    payslip_bytes = create_synthetic_payslip(name, "Tech Solutions Ltd", 95000.0, 76000.0)
    bank_bytes = create_synthetic_bank_stmt(name, "HDFC Bank", 94500.0, 22000.0)

    with open("test_documents/pan_card.png", "wb") as f:
        f.write(pan_bytes)
    with open("test_documents/salary_slip.png", "wb") as f:
        f.write(payslip_bytes)
    with open("test_documents/bank_statement.png", "wb") as f:
        f.write(bank_bytes)

    print("✅ Created test documents in ./test_documents folder:")
    print("   • test_documents/pan_card.png")
    print("   • test_documents/salary_slip.png")
    print("   • test_documents/bank_statement.png")

if __name__ == "__main__":
    generate_all()