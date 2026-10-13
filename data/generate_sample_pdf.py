"""Helper script to generate a valid sample FESCO computerized bill PDF."""

import os

def create_sample_pdf(output_path: str = "data/sample_fesco_bill.pdf") -> str:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    
    # Text stream containing authentic FESCO computerized bill data
    bill_content = (
        "FAISALABAD ELECTRIC SUPPLY COMPANY (FESCO)\n"
        "ELECTRICITY BILL FOR THE MONTH OF SEP-2026\n"
        "NAME: HAJI ABDUL WAHEED\n"
        "ADDRESS: HOUSE #108 STREET #4, GULBERG COLONY, FAISALABAD\n"
        "REFERENCE NO: 13 13124 1234567 U\n"
        "TARIFF: A-1a(01) DOMESTIC\n"
        "SANCTIONED LOAD: 7.0 KW\n"
        "FEEDER: GULBERG EXPRESS 11KV\n"
        "METER NO: FES-742918\n"
        "CURRENT READING UNITS: 680\n"
        "PAYABLE WITHIN DUE DATE: 35360\n"
        "BILLING HISTORY:\n"
        "OCT-25 450 22500\n"
        "NOV-25 320 16000\n"
        "DEC-25 280 14000\n"
        "JAN-26 260 13000\n"
        "FEB-26 310 15500\n"
        "MAR-26 420 21000\n"
        "APR-26 550 27500\n"
        "MAY-26 720 36000\n"
        "JUN-26 890 44500\n"
        "JUL-26 920 46000\n"
        "AUG-26 840 42000\n"
        "SEP-26 680 34000\n"
    )

    # Format text into a minimal standard uncompressed PDF document
    escaped_text = bill_content.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream_lines = escaped_text.split("\n")
    stream_ops = ["BT", "/F1 12 Tf", "50 750 Td", "14 TL"]
    for idx, line in enumerate(stream_lines):
        if idx == 0:
            stream_ops.append(f"({line}) Tj")
        else:
            stream_ops.append(f"T* ({line}) Tj")
    stream_ops.append("ET")
    stream_data = "\n".join(stream_ops)
    stream_len = len(stream_data.encode("latin1"))

    pdf_template = f"""%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>
endobj
4 0 obj
<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>
endobj
5 0 obj
<< /Length {stream_len} >>
stream
{stream_data}
endstream
endobj
xref
0 6
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000224 00000 n 
0000000301 00000 n 
trailer
<< /Size 6 /Root 1 0 R >>
startxref
{stream_len + 360}
%%EOF"""

    with open(output_path, "wb") as f:
        f.write(pdf_template.encode("latin1"))
    return output_path

if __name__ == "__main__":
    path = create_sample_pdf()
    print(f"Generated sample bill: {path}")
