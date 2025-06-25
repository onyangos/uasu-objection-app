# app.py
import os
import sys
import signal
import subprocess
import datetime
import base64
from flask import Flask, render_template, request, redirect, url_for, session
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import webbrowser

# Kill port 5000 if occupied
def free_port_5000():
    if os.environ.get('RENDER') == 'true':
        return  # skip port cleanup on Render
    try:
        current_pid = os.getpid()
        result = subprocess.run(['lsof', '-ti:5000'], stdout=subprocess.PIPE, text=True)
        for pid in result.stdout.strip().split('\n'):
            if pid.isdigit() and int(pid) != current_pid:
                os.kill(int(pid), signal.SIGKILL)
                print(f"✔ Killed process {pid} using port 5000")
    except Exception as e:
        print(f"⚠ Failed to free port 5000: {e}")

free_port_5000()


app = Flask(__name__)
app.secret_key = 'replace-this-with-a-random-secret-key'

SCOPES = ['https://www.googleapis.com/auth/gmail.send']
import json

CLIENT_SECRETS_FILE = 'temp_credentials.json'
with open(CLIENT_SECRETS_FILE, 'w') as f:
    f.write(os.environ['GOOGLE_CREDENTIALS_JSON'])


# --- Fixed Content ---
FIXED_CONTENT = {
    "PROCEDURAL_VIOLATIONS": """1. Fraudulent Adoption Process
• No secret ballot was conducted. This is confirmed by the minutes presented by Dr. Wasonga, your letter dated 20th December 2024, and the testimony of 103 delegates who travelled to attend the 32nd NDC and confirmed that no voting took place on 10th December 2024.
• Relevant provisions:
   – UASU 2014 Constitution Articles 14(a) and 23: Require approval by secret ballot with a two-thirds delegate majority.
   – Labour Relations Act (LRA) Section 34(3)(b): Mandates the use of secret ballots for constitutional amendments.
   – Constitution of Kenya (COK) Article 47: Guarantees the right to fair administrative action.

2. Fabricated Minutes and Results
• Official communications reported specific voting outcomes despite the absence of any voting process.
• Violation:
   – LRA Section 34(5): Requires accurate record-keeping for union decisions.

3. Lack of Oversight
• The National Delegates Conference (NDC) was conducted without the presence of an electoral board or Labour Officer.
• Breach:
   – LRA Section 34(1)(d): Requires impartial internal dispute resolution and proper oversight mechanisms.""",

    "SUBSTANTIVE_ILLEGALITIES": """1. Unelected Delegates
• Articles 12(3)(a), 29(1)(e), and 40(5) of the draft grant automatic delegate status to national officials.
• This conflicts with:
   – LRA Section 34(1)(b): Delegates must be elected by union members.
   – LRA Section 34(2)(a): Constitutions shall not contain provisions that unfairly discriminate between incumbents and other candidates in union elections.
   – COK Article 41(1)(c): Ensures fair representation within trade unions.

2. Unlawful Term Extension
• Article 40(5) extends NEC terms to two consecutive 5-year terms as delegates.
• This contravenes:
   – LRA Section 34(3)(a): Limits union leadership terms to five years, renewable only through re-election.

3. Centralization of Financial Powers
• Article 13(3)(g) grants the National Executive Council (NEC) unilateral financial authority.
• This violates:
   – LRA Section 49(1): Requires transparent and accountable financial management.
   – UASU 2014 Constitution Article 13(c): Entrusts financial oversight to Trustees.

4. Arbitrary Dissolution of Branches
• Article 10(5) allows NEC to dissolve branches with fewer than 20 members.
• This is unlawful under:
   – LRA Section 34(1): Requires participatory and consultative governance.
   – COK Article 10(2)(a): Upholds public participation as a constitutional principle.""",

    "ADDITIONAL_GROUNDS": """1. Insufficient Notice Period
• The draft constitution was circulated on 27th November 2024 for a meeting scheduled on 10th December 2024.
• This violates:
   – UASU 2014 Constitution Article 23: Requires at least 14 days' notice to members.

2. Irregular Gazette Publication
• Although dated 5th February 2025, Gazette Notice No. 8134 was only published on 22nd June 2025 — a delay of 135 days.
• This raises legal concerns under:
   – LRA Section 27(4): Objection period begins at the time of actual publication.
   – Penal Code Section 347: Criminalizes false or backdated documentation.

3. Exclusion of Trustees from Oversight
• Article 17(2) removes Trustees from participating in financial decisions.
• This breaches:
   – LRA Section 49(1): Establishes standards for transparent union finances.""",

    "REQUESTED_ACTIONS": """1. Reject the registration of the Draft UASU Constitution 2024.

2. Investigate the procedural irregularities, including:
   • Fabrication of voting records and conference minutes.
   • Backdating of Gazette Notice No. 8134.

3. Direct UASU to:
   • Convene a fresh and compliant National Delegates Conference under Labour Officer supervision.
   • Conduct secret ballot voting in line with statutory and constitutional requirements.
   • Ensure that any constitutional amendments comply with the Labour Relations Act and the Constitution of Kenya."""
}


@app.route('/')
def index():
    return render_template('form.html')

@app.route('/authorize')
def authorize():
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES)
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    auth_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
    session['state'] = state
    return redirect(auth_url)

@app.route('/oauth2callback')
def oauth2callback():
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    state = session['state']
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = url_for('oauth2callback', _external=True)
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    session['credentials'] = {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }
    return redirect(url_for('form'))

@app.route('/form', methods=['GET', 'POST'])
def form():
    if request.method == 'POST':
        data = request.form.to_dict()
        data['preview_date'] = datetime.date.today().strftime('%B %d, %Y')
        session['form_data'] = data
        return render_template('preview.html', data=data, fixed=FIXED_CONTENT)
    return render_template('form.html')

@app.route('/submit', methods=['POST'])
def submit():
    data = session.get('form_data')
    creds = session.get('credentials')
    if not data:
        return redirect(url_for('form'))
    if not creds:
        return redirect(url_for('authorize'))
    file_path = create_pdf(data)
    send_email(creds, data, file_path)
    return render_template('success.html', name=data['name'])

def create_pdf(data):
    filename = f"UASU_Objection_{data['id_number']}.pdf"
    path = os.path.join('static', filename)
    doc = SimpleDocTemplate(path, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    story = []

    paragraphs = f"""
To,\nThe Registrar of Trade Unions\nState Department for Labour and Skill Development\nBishops Road, Social Security House\nP.O. Box 40326 – 00100\nNairobi\n\n{datetime.date.today().strftime('%B %d, %Y')}\n\nDear Madam,\n\nREF: Objection to the Proposed Amendments to the UASU 2024 Constitution – Gazette Notice No. 8134\n\nI am writing to formally object to the proposed amendments to the Constitution of the Universities Academic Staff Union (UASU), as published in Gazette Notice No. 8134 dated 5th February 2025 and released to the public on 22nd June 2025. I am a member of UASU, currently affiliated with {data['university']}, and my personal details are provided below:\n\nFull Name: {data['name']}\nPF/Staff Number: {data['pf_number']}\nID Number: {data['id_number']}\nEmail: {data['email']}\n\nMy grounds for objection are as follows:\n\nI. PROCEDURAL VIOLATIONS\n{FIXED_CONTENT['PROCEDURAL_VIOLATIONS']}\n\nII. SUBSTANTIVE ILLEGALITIES\n{FIXED_CONTENT['SUBSTANTIVE_ILLEGALITIES']}\n\nIII. ADDITIONAL GROUNDS FOR OBJECTION\n{FIXED_CONTENT['ADDITIONAL_GROUNDS']}\n\n{data.get('additional_reasons', '').strip()}\n\nIV. REQUESTED ACTIONS\n{FIXED_CONTENT['REQUESTED_ACTIONS']}\n\nThis objection is filed under Section 27(4) of the Labour Relations Act (LRA) and Article 41 of the Constitution of Kenya (COK). Kindly acknowledge receipt and take the necessary action to uphold the rule of law and union democracy.\n\nYours sincerely,\n\n{data['name']}\nDate: {datetime.date.today().strftime('%B %d, %Y')}
"""

    for line in paragraphs.strip().split("\n"):
        story.append(Paragraph(line.strip(), styles['Normal']))
        story.append(Spacer(1, 12))

    doc.build(story)
    return path

def send_email(credentials_dict, data, pdf_path):
    creds = Credentials.from_authorized_user_info(credentials_dict)
    service = build('gmail', 'v1', credentials=creds)

    message = MIMEMultipart()
    message['to'] = "rejectuasu2024constitution@gmail.com"
    message['cc'] = data['email']
    message['bcc'] = "rejectuasu2024constitution@gmail.com"
    message['from'] = data['email']
    message['subject'] = f"Objection – UASU Constitution (ID {data['id_number']})"
    message.attach(MIMEText("Please find attached my objection letter.", "plain"))

    with open(pdf_path, 'rb') as f:
        part = MIMEBase('application', 'pdf')
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
        message.attach(part)

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw}).execute()

def cleanup_on_exit(signal_received, frame):
    print("\nStopping Flask and freeing port 5000...")
    try:
        current_pid = os.getpid()
        result = subprocess.run(['lsof', '-ti:5000'], stdout=subprocess.PIPE, text=True)
        for pid in result.stdout.strip().split('\n'):
            if pid.isdigit() and int(pid) != current_pid:
                os.kill(int(pid), signal.SIGKILL)
                print(f"✔ Killed process {pid} using port 5000")
    except Exception as e:
        print(f"⚠ Error cleaning up: {e}")
    sys.exit(0)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, cleanup_on_exit)
    signal.signal(signal.SIGTERM, cleanup_on_exit)
    if os.environ.get("RENDER") != "true":
        import threading
        import time
        def open_browser():
            time.sleep(1.5)
            webbrowser.open("http://127.0.0.1:5000")
        threading.Thread(target=open_browser).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)


