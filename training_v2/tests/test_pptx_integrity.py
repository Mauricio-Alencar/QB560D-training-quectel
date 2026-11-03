"""Regression fixtures for the notes-master Office repair defect."""
import io
import sys
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'host'))
from pptx_integrity import notes_master_problems


def fixture(masters=1, note_target=1):
    p='http://schemas.openxmlformats.org/presentationml/2006/main'
    r='http://schemas.openxmlformats.org/officeDocument/2006/relationships'
    package='http://schemas.openxmlformats.org/package/2006/relationships'
    content='http://schemas.openxmlformats.org/package/2006/content-types'
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        z.writestr('ppt/presentation.xml','<p:presentation xmlns:p="'+p+'" xmlns:r="'+r+'"><p:notesMasterIdLst>'+''.join('<p:notesMasterId r:id="m%d"/>'%i for i in range(1,masters+1))+'</p:notesMasterIdLst></p:presentation>')
        z.writestr('ppt/_rels/presentation.xml.rels','<Relationships xmlns="'+package+'">'+''.join('<Relationship Id="m%d" Type="%s/notesMaster" Target="notesMasters/notesMaster%d.xml"/>'%(i,r,i) for i in range(1,masters+1))+'</Relationships>')
        z.writestr('[Content_Types].xml','<Types xmlns="'+content+'">'+''.join('<Override PartName="/ppt/notesMasters/notesMaster%d.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.notesMaster+xml"/>'%i for i in range(1,masters+1))+'</Types>')
        for i in range(1,masters+1):z.writestr('ppt/notesMasters/notesMaster%d.xml'%i,'<p:notesMaster xmlns:p="'+p+'"/>')
        z.writestr('ppt/notesSlides/notesSlide1.xml','<p:notes xmlns:p="'+p+'"/>')
        z.writestr('ppt/notesSlides/_rels/notesSlide1.xml.rels','<Relationships xmlns="'+package+'"><Relationship Id="m" Type="'+r+'/notesMaster" Target="../notesMasters/notesMaster%d.xml"/></Relationships>'%note_target)
    stream.seek(0)
    return zipfile.ZipFile(stream)


class NotesMasterTests(unittest.TestCase):
    def test_accepts_single_shared_master(self):
        with fixture() as archive:self.assertEqual(notes_master_problems(archive),[])

    def test_rejects_merged_multiple_masters(self):
        with fixture(masters=4) as archive:
            problems=notes_master_problems(archive)
        self.assertTrue(any('found 4' in p for p in problems))
        self.assertTrue(any('multiple notes-master parts' in p for p in problems))

    def test_rejects_a_stale_notes_reference(self):
        with fixture(note_target=2) as archive:
            problems=notes_master_problems(archive)
        self.assertTrue(any('does not use the single canonical' in p for p in problems))


if __name__=='__main__':
    unittest.main()
