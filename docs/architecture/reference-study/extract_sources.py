"""Read-only extraction of the user-specified comparison corpus; no document macros."""
from pathlib import Path
import concurrent.futures, hashlib, json, urllib.request, zipfile, xml.etree.ElementTree as ET
from pypdf import PdfReader

ROOT=Path(__file__).parent
(ROOT/'downloads').mkdir(parents=True,exist_ok=True)
(ROOT/'text').mkdir(exist_ok=True)
LOCAL=[('L01','Preliminary Testimony.doc'),('L02','preliminaryquestionswithoutvalidation.docx'),('L03','preliminaryquestionswithvalidation.docx'),('L04','Radical Sanation.doc'),('L05','Lack of Form Petition.doc'),('L06','Witness Testimony - Formal Case.docx'),('L07','Comprehensive Testimony.doc'),('L08','Prior Spouse Report HH.doc')]
REMOTE=[
('R01','El Paso petition and questionnaire','https://www.elpasodiocese.org/uploads/5/4/9/5/54952711/petitionandquestionnaireformarriagenullity1012015.pdf'),
('R02','San Jose Form C','https://www.dsj.org/wp-content/uploads/2016/01/FORM-C-01-05-2016-v-2a.pdf'),
('R03','Philadelphia petitioner questionnaire','https://archphila.org/wp-content/uploads/2015/12/Petitioner-Questionnaire.pdf'),
('R04','Charleston preliminary questionnaire','https://charlestondiocese.org/wp-content/uploads/2021/06/Preliminary-Questionnaire-Update-2021.pdf'),
('R05','New Orleans marriage annulment questionnaire','https://nolacatholic.org/documents/2017/10/MARRIAGE_ANNULMENT_QUESTIONNAIRE-1.pdf'),
('R06','Los Angeles formal trial packet','https://lacatholics.org/wp-content/uploads/2022/04/Fillable-2019-FORMAL-TRIAL-October-23-2019no-highlight.pdf'),
('R07','Spanish formal case packet','https://files.ecatholic.com/15442/documents/2024/7/Formal%20Case%20Packet%20-%20Spanish%20v5-6-19b.pdf?t=1720721689000'),
('R08','Sacramento Form C','https://www.scd.org/sites/default/files/2017-11/FORM%20C%20-%20English_Nov2017.pdf'),
('R09','Arlington convalidation supplement','https://www.arlingtondiocese.org/media-files/uploadedFiles/CDA/Assets/PDF/Canonical_Affairs_and_Tribunal/Forms/Supplemental%20Questions%20for%20Convalidation%20v%200122.pdf'),
('R10','Ordinary RTS English packet','https://files.ecatholic.com/32494/documents/2025/11/2.%20ENGLISH%20-%20ORDINARY%20RTS%20new.pdf?t=1762990993000'),
('R11','Briefer RTS English packet','https://files.ecatholic.com/32494/documents/2025/10/1.%20ENGLISH%20-%20BRIEFER%20RTS-2.pdf?t=1761830149000'),
('R12','Venice marital dispensation or permission','https://cdn.diocesanweb.org/crossroads/dioceseofvenice/wp-content/uploads/Marital-Dispensation-or-Permission-Form.pdf'),
('R13','Venice formal case application','https://cdn.diocesanweb.org/crossroads/dioceseofvenice/wp-content/uploads/Application-Declaration-of-Nullity-Formal-Case-WEBSITE.pdf'),
('R14','Philadelphia witness questionnaire','https://archphila.org/wp-content/uploads/2016/01/Witness-Questionnaire.pdf')]

def docx_extract(path):
    with zipfile.ZipFile(path) as z:
        doc=ET.fromstring(z.read('word/document.xml'))
        ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
        lines=[]
        for p in doc.findall('.//w:p',ns):
            text=''.join(p.itertext()) if False else ''.join(t.text or '' for t in p.findall('.//w:t',ns))
            if text.strip(): lines.append(f'P{len(lines)+1:03d}: {text.strip()}')
        return '\n'.join(lines),len(lines)

def extract_pdf(path):
    r=PdfReader(path)
    parts=[f'=== PDF PAGE {i+1} ===\n{p.extract_text() or ""}' for i,p in enumerate(r.pages)]
    return '\n\n'.join(parts),len(r.pages)

def remote(row):
    sid,title,url=row
    out=ROOT/'downloads'/f'{sid}.pdf'
    record={'id':sid,'title':title,'url':url,'status':'unavailable'}
    try:
        if not out.exists():
            req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0 (compatible; document comparison)'})
            with urllib.request.urlopen(req,timeout=40) as response:
                data=response.read(40_000_001)
                if len(data)>40_000_000: raise ValueError('Source exceeds 40 MB review download limit')
                if not data.startswith(b'%PDF'): raise ValueError('Response is not a PDF')
                out.write_bytes(data)
                record['resolved_url']=response.url
        text,count=extract_pdf(out)
        (ROOT/'text'/f'{sid}.txt').write_text(text,encoding='utf-8')
        record.update(status='extracted',pages=count,characters=len(text),sha256=hashlib.sha256(out.read_bytes()).hexdigest(),text_path=f'text/{sid}.txt')
    except Exception as e: record['error']=str(e)
    print(sid,record['status'],record.get('pages',''),record.get('error',''),flush=True)
    return record

if __name__=='__main__':
    records=[]
    for sid,name in LOCAL:
        p=Path('C:/Users/AdminMan/Downloads')/name
        record={'id':sid,'title':name,'local_path':str(p),'status':'unavailable'}
        try:
            text,count=docx_extract(p)
            (ROOT/'text'/f'{sid}.txt').write_text(text,encoding='utf-8')
            record.update(status='extracted',format='OOXML ZIP even where filename ends .doc',paragraphs=count,characters=len(text),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),text_path=f'text/{sid}.txt')
        except Exception as e: record['error']=str(e)
        records.append(record)
        print(sid,record['status'],record.get('paragraphs',''),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool: records.extend(pool.map(remote,REMOTE))
    (ROOT/'source-manifest.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
