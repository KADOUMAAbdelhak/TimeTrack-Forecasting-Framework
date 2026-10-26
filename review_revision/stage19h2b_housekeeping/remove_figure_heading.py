"""Remove only the original Figure 1 heading text block; preserve vector geometry."""
from pathlib import Path
import hashlib,json
from pypdf import PdfReader,PdfWriter
from pypdf.generic import DecodedStreamObject
ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
REL='manuscript/jss/figures/framework_s1_s2_m1.pdf'
source=OUT/'archive'/REL;target=ROOT/REL
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
if sha(source)!=sha(target):
    previous=json.loads((OUT/'figure_vector_check.json').read_text())
    assert previous['before_sha256']==sha(source) and previous['after_sha256']==sha(target)
reader=PdfReader(source);writer=PdfWriter();writer.clone_document_from_reader(reader)
page=writer.pages[0];old=page.get_contents().get_data()
start=old.index(b'BT\n');end=old.index(b'\nET',start)+3
heading=old[start:end]
assert b'(Multiva)' in heading and b'(input)' in heading and b'(resentation)' in heading
assert heading.count(b'TJ')==4 and b'(=)' in heading
updated=old[:start]+b'BT\nET'+old[end:]
stream=DecodedStreamObject();stream.set_data(updated);page.replace_contents(stream.flate_encode())
with target.open('wb') as output:writer.write(output)
new=PdfReader(target).pages[0]
assert new.get_contents().get_data()==updated
assert tuple(new.mediabox)==tuple(reader.pages[0].mediabox)
assert new.extract_text().strip()==reader.pages[0].extract_text().split('\n',1)[1].strip()
result=dict(status='PASS',edit='First heading-only BT/ET text object replaced by an empty text object',
    deleted_heading='Multivariate input != shared representation',deleted_text_show_operators=4,
    all_other_content_stream_bytes_identical=True,mediabox_identical=True,
    all_nonheading_extracted_text_identical=True,before_sha256=sha(source),after_sha256=sha(target))
(OUT/'figure_vector_check.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
