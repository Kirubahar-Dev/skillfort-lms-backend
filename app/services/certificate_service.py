import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


class CertificateService:
    def __init__(self, storage_dir: str):
        self.storage_dir = Path(storage_dir)
        self.cert_dir = self.storage_dir / "certificates"
        self.cert_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, certificate_no: str, student_name: str, course_name: str) -> str:
        file_path = self.cert_dir / f"{certificate_no}.pdf"
        c = canvas.Canvas(str(file_path), pagesize=A4)
        width, height = A4
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(width / 2, height - 120, "Skillfort Institute")
        c.setFont("Helvetica", 16)
        c.drawCentredString(width / 2, height - 180, "Certificate of Completion")
        c.setFont("Helvetica", 13)
        c.drawCentredString(width / 2, height - 250, "This certifies that")
        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(width / 2, height - 290, student_name)
        c.setFont("Helvetica", 13)
        c.drawCentredString(width / 2, height - 330, "has successfully completed")
        c.setFont("Helvetica-Bold", 18)
        c.drawCentredString(width / 2, height - 365, course_name)
        c.setFont("Helvetica", 11)
        c.drawCentredString(width / 2, 70, f"Certificate No: {certificate_no}")
        c.showPage()
        c.save()
        return str(file_path)
