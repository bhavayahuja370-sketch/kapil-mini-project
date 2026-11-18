import re
import tempfile
import unittest
from pathlib import Path

from app import app, init_db, db, ADMIN_PASSWORD

class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        app.config.update(TESTING=True, DATABASE=str(Path(self.tmp.name)/'test.db'))
        init_db()
        self.client = app.test_client()
        self.client.get('/')
        with self.client.session_transaction() as s:
            self.csrf = s['csrf']

    def tearDown(self):
        self.tmp.cleanup()

    def post(self, path, **data):
        return self.client.post(path, data={'csrf':self.csrf, **data}, follow_redirects=True)

    def test_complete_workflow(self):
        response = self.post('/register/1', name='Test Student',roll='BCA001',email='test@example.com',course='BCA 3-A')
        self.assertIn(b'CONFIRMED PASS',response.data)
        with db() as conn:
            token=conn.execute('SELECT token FROM registrations').fetchone()[0]
        qr=self.client.get('/qr/'+token+'.png')
        self.assertTrue(qr.data.startswith(b'\x89PNG'))
        self.assertIn(b'already registered',self.post('/register/1',name='Test',roll='BCA001',email='a@b.com',course='BCA').data)
        self.assertEqual(self.client.get('/export/1').status_code,302)
        self.assertIn(b'Organizer hub',self.post('/login',password=ADMIN_PASSWORD).data)
        self.assertIn(b'different event',self.post('/checkin',token=token,event='2').data)
        self.assertIn(b'Invalid QR',self.post('/checkin',token='bad',event='1').data)
        self.assertIn(b'Check-in successful',self.post('/checkin',token=token,event='1').data)
        self.assertIn(b'Duplicate entry blocked',self.post('/checkin',token=token,event='1').data)
        self.assertIn(b'Test Student',self.client.get('/export/1').data)
        self.assertIn(b'Your event is ready',self.post('/events',title='Test Fest',category='Culture',date='2026-12-10T10:00',venue='Hall',description='A test event').data)
        self.assertIn(b'Test Fest',self.client.get('/').data)

    def test_validation_and_csrf(self):
        self.assertEqual(self.client.post('/login',data={'password':ADMIN_PASSWORD}).status_code,400)
        self.assertIn(b'valid details',self.post('/register/1',name='',roll='',email='bad',course='').data)
        self.assertEqual(self.client.get('/pass/invalid').status_code,404)
        self.assertEqual(self.client.get('/register/999').status_code,404)

if __name__ == '__main__':
    unittest.main()
