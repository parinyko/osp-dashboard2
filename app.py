from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
from threading import Thread, RLock
from datetime import datetime
from zoneinfo import ZoneInfo
import os, json, glob, io
import pandas as pd

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key')
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
TZ = ZoneInfo('Asia/Bangkok')
REMARK_FILE, CONTACT_FILE = 'remarks.json', 'contacts.json'
REMARK_LOCK, CONTACT_LOCK = RLock(), RLock()
VALID_SUBSYSTEMS = ['EDS-OSP','ETS-OSP','FTTB-OSP','FTTH-OSP','FTTX-OSP','Splitter-OSP','Transmission-OSP','EDS SW NODE-OSP','EDS IPLC-OSP']
TEAM_DATA = [
 ('DMP','Dmplocallatkrabang A'),('DMP','Dmplocallatkrabang B'),('DMP','Dmplocallatkrabang C'),
 ('DMP','Dmplocalpathumthani A'),('DMP','Dmplocalpathumthani B'),('DMP','Dmplocalpathumthani C'),
 ('Origin','Originlocal Center'),('Origin','Originlocalthungkhru A'),('Origin','Originlocalthungkhru B'),('Origin','Originlocalthungkhru C'),
 ('Origin','Originlocalnonthaburi A'),('Origin','Originlocalnonthaburi B'),('Origin','Originlocalnonthaburi C'),
 ('EDS BKK','Exeds A'),('EDS BKK','Exeds B'),
 ('SCT','Exsct A'),('SCT','Exsct B'),('SCT','Exsct C'),('SCT','Extrsct E'),
 ('BPL','Exbpl A'),('BPL','Exbpl B'),('BPL','Exbpl C'),('BPL','Exbpl D'),('BPL','Exbpl E'),('BPL','Extrbpl F'),('BPL','Extrbpl G'),
 ('TLC','Extlc A'),('TLC','Extlc B'),('TLC','Extlc C'),('TLC','Extlc D'),('TLC','Extlc E'),('TLC','Extrtlc F'),
 ('CWT','Excwt A'),('CWT','Excwt B'),('CWT','Excwt C'),('CWT','Excwt D'),('CWT','Excwt E'),('CWT','Extrcwt F'),('CWT','Extrcwt G'),
 ('Team Spare','Exspare A'),('Team Spare','Exspare B'),('Team Spare','Exspare C'),('Team Spare','Exspare D'),('Team Spare','Exspare E'),('Team Spare','Exspare F'),('Team Spare','Exspare G'),('Team Spare','Exspare H'),('Team Spare','Exspare I')]
DASHBOARD_EXCLUDED_ZONES = {'BKK2','SPK','NTB','AIS'}
ASSIGN_ORDER = [u for _,u in TEAM_DATA]
AREA_DATA = {u: '' for _,u in TEAM_DATA}
AREA_DATA.update({'Exspare A':'All Zone'})
def load_json(path):
    try:
        with open(path, encoding='utf-8') as f:
            x=json.load(f); return x if isinstance(x,dict) else {}
    except (OSError, ValueError): return {}
REMARKS, CONTACTS = load_json(REMARK_FILE), load_json(CONTACT_FILE)
RAW_DATA=[]; LAST_UPDATE='-'

def clean(v): return str(v if v is not None else '').strip()
def dashboard_teams(): return [{'zone':z,'user':u} for z,u in TEAM_DATA if z not in DASHBOARD_EXCLUDED_ZONES]
def status_color(s):
    s=clean(s).lower()
    if 'on-site' in s or 'onsite' in s: return '#c6efce'
    if 'departed' in s: return '#ffe699'
    if 'assigned' in s or 'accepted' in s: return '#ffc7ce'
    if 'held' in s: return '#9fd5ff'
    return '#ffffff'
def prepare_jobs(df):
    if df.empty: return df
    for c in ['Sub System','Status','Priority','Assign to']:
        if c not in df.columns: df[c]=''
    sub=df['Sub System'].fillna('').astype(str).str.strip()
    st=df['Status'].fillna('').astype(str).str.lower()
    pr=df['Priority'].fillna('').astype(str).str.lower().str.strip()
    out=df[sub.isin(VALID_SUBSYSTEMS) & ~st.str.contains('done(not leave)',regex=False) & pr.ne('') & pr.ne('none')].copy()
    order={u:i for i,u in enumerate(ASSIGN_ORDER)}
    out['_order']=out['Assign to'].fillna('').astype(str).str.strip().map(order).fillna(9999)
    return out.sort_values(['_order','Assign to']).drop(columns=['_order'])
def load_excel():
    global RAW_DATA, LAST_UPDATE
    files=sorted(glob.glob(os.path.join(UPLOAD_FOLDER,'*.xlsx'))+glob.glob(os.path.join(UPLOAD_FOLDER,'*.xls')),key=os.path.getmtime)
    if files:
        df=pd.read_excel(files[-1]); RAW_DATA=df.fillna('').to_dict('records'); LAST_UPDATE=datetime.fromtimestamp(os.path.getmtime(files[-1]),TZ).strftime('%d/%m/%Y %H:%M:%S')
def dashboard_rows():
    df=prepare_jobs(pd.DataFrame(RAW_DATA)); rows=[]
    for team in dashboard_teams():
        user=team['user']; jobs=df[df['Assign to'].astype(str).str.strip().str.casefold()==user.casefold()] if not df.empty else pd.DataFrame()
        statuses=sorted(set(clean(s) for s in jobs.get('Status',[]) if clean(s)),key=str.casefold)
        st=', '.join(statuses); low=st.lower()
        work='On-site' if ('on-site' in low or 'onsite' in low) else ('Departed' if 'departed' in low else ('Working' if len(jobs) else 'ว่าง'))
        rows.append({'zone':team['zone'],'user':user,'area':AREA_DATA.get(user,''),'work_status':work,'job_count':len(jobs),'status_text':st,'status_color':status_color(st),'contact':CONTACTS.get(user,''),'remark':REMARKS.get(user,'')})
    return rows
@app.route('/')
def index():
    df=prepare_jobs(pd.DataFrame(RAW_DATA)); totals={'total_jobs':len(df),'total_critical':0,'total_major':0,'total_minor':0}
    if not df.empty:
        p=df['Priority'].astype(str).str.lower().str.strip(); totals.update(total_critical=int((p=='critical').sum()),total_major=int((p=='major').sum()),total_minor=int((p=='minor').sum()))
    zone_summary=[]
    for z in sorted(set(x['zone'] for x in TEAM_DATA)):
        users=[x['user'] for x in TEAM_DATA if x[0]==z]
        zone_summary.append({'zone':z,'jobs':int(df['Assign to'].astype(str).isin(users).sum()) if not df.empty else 0})
    rows=dashboard_rows(); counts={'total':len(rows),'working':sum(r['work_status']=='Working' for r in rows),'onsite':sum(r['work_status']=='On-site' for r in rows),'departed':sum(r['work_status']=='Departed' for r in rows),'free':sum(r['work_status']=='ว่าง' for r in rows),'missing':0,'late':0,'ready':sum(r['work_status'] in ('ว่าง','On-site') for r in rows)}
    return render_template('home.html',**totals,last_update=LAST_UPDATE,zone_summary=zone_summary,team_summary=counts,osp_aging_summary=[],done_not_leave_by_group=[])
@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    return render_template('index.html', rows=dashboard_rows(), last_update=LAST_UPDATE, teams=dashboard_rows())
@app.route('/resource_monitor')
def resource_monitor():
    return render_template('resource_monitor.html', rows=dashboard_rows(), teams=dashboard_rows(), last_update=LAST_UPDATE, dates=[], selected_date='')
@app.route('/job_monitor')
def job_monitor():
    return render_template('job_monitor.html', jobs=RAW_DATA, last_update=LAST_UPDATE,total_jobs=len(RAW_DATA),total_critical=0,total_major=0,total_minor=0,total_sct=0,total_cwt=0,total_ont=0,total_tlc=0)
@app.route('/daily_osp_remain')
def daily_osp_remain(): return render_template('daily_osp_remain.html', records=[])
@app.route('/save_remark', methods=['POST'])
def save_remark():
    data=request.get_json(silent=True) or request.form; user=clean(data.get('user')); REMARKS[user]=clean(data.get('remark'))
    with REMARK_LOCK:
        with open(REMARK_FILE+'.tmp','w',encoding='utf-8') as f: json.dump(REMARKS,f,ensure_ascii=False,indent=2)
        os.replace(REMARK_FILE+'.tmp',REMARK_FILE)
    return jsonify(success=True,user=user,remark=REMARKS[user])
@app.route('/save_contact', methods=['POST'])
def save_contact():
    data=request.get_json(silent=True) or request.form; user=clean(data.get('user')); CONTACTS[user]=clean(data.get('contact'))
    with CONTACT_LOCK:
        with open(CONTACT_FILE+'.tmp','w',encoding='utf-8') as f: json.dump(CONTACTS,f,ensure_ascii=False,indent=2)
        os.replace(CONTACT_FILE+'.tmp',CONTACT_FILE)
    return jsonify(success=True,user=user,contact=CONTACTS[user])
@app.route('/upload', methods=['POST'])
def upload():
    f=request.files.get('file') or request.files.get('excel')
    if not f or not f.filename.lower().endswith(('.xlsx','.xls')): return 'กรุณาเลือกไฟล์ Excel',400
    dest=os.path.join(UPLOAD_FOLDER,os.path.basename(f.filename)); f.save(dest); load_excel(); return redirect(url_for('index'))
@app.route('/export_excel')
def export_excel():
    df=pd.DataFrame(RAW_DATA); b=io.BytesIO(); df.to_excel(b,index=False); b.seek(0); return send_file(b,download_name='jobs.xlsx',as_attachment=True)
@app.route('/export_dashboard_excel')
def export_dashboard_excel():
    b=io.BytesIO(); pd.DataFrame(dashboard_rows()).to_excel(b,index=False); b.seek(0); return send_file(b,download_name='resource_dashboard.xlsx',as_attachment=True)
if __name__=='__main__':
    load_excel()
    app.run(host='0.0.0.0',port=int(os.environ.get('PORT',5000)),debug=False)
