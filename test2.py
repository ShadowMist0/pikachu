from fpdf import FPDF

pdf = FPDF()
pdf.add_page()
pdf.set_font("Arial", size=10, style="B")
pdf.cell(190,10,"ATTENDANCE SHEET",ln=1, align="C")
pdf.set_font("Arial",size=8)
pdf.cell(62, 5, "date: 9-8-8", align="L")
pdf.cell(62, 5, "subject", align="C")
pdf.cell(62, 5, "teacher",ln=1,align="R")
pdf.cell(10,5,"SI", border=1)
pdf.cell(60,5,"Roll", border=1)
pdf.cell(60,5,"Name", border=1)
pdf.cell(60,5,"Status", border=1, ln=1)
students = [i for i in range(2403121, 2403181)]
for student in students:
    pdf.cell(10,4,f"{student-2403120}", border=1)
    pdf.cell(60,4,f"{student}", border=1)
    pdf.cell(60,4,"hi", border=1)
    pdf.cell(60,4,"A", border=1, ln=1)




file_name="hi.pdf"
pdf.output(file_name)