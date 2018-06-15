from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import mimetypes
import getpass
import smtplib
import csv
import re
from time import sleep
from collections import namedtuple

# Global setup
testResults = "wyniki.csv"
emailFrom = "John Doe <john.doe@example.com>"
emailSubject = "Wyniki kolokwium z dnia X xxxxxxx XXXX"
fileBody = "email.txt"
fileAttach = "run.py"
mailServer = "xxxx.xxx.xxxx.pl"
mailUser = "borys.szefczyk"
dryRun = False


class Score(object):
    """Store decimal numbers as integers and convert them to grades
    directly, taking care of correct comparison.

    Rationale:
    Suppose the student needs 10.3 points to pass.
    score = 10.2
    score += 0.1
    The student should pass, however floating point arithmetics
    gives score = 10.299999999999999 and the comparison
    score >= 10.3
    produces False."""

    precision = 1

    grading = [
        (-4, 15, "2.0", "niedostateczny"),
        (15, 17.5, "3.0", "dostateczny"),
        (17.5, 20, "3.5", "dostateczny+"),
        (20, 22.5, "4.0", "dobry"),
        (22.5, 25, "4.5", "dobry+"),
        (25, 27.5, "5.0", "bardzo dobry"),
        (27.5, 30, "5.5", "celujący"),
    ]

    def __init__(self, val):
        if isinstance(val, str):
            val = float(val)
        if isinstance(val, int):
            val *= Score.factor()
        elif isinstance(val, float):
            val = round(val * Score.factor())
        if not isinstance(val, int):
            raise TypeError("Accepted types are int, float and str")
        self.value = val

    @classmethod
    def factor(cls):
        """Returns factor to shift decimal point of the number"""
        return 10**cls.precision

    def __float__(self):
        return float(self.value / Score.factor())

    def __str__(self):
        return "{:.1f}".format(float(self))

    def __repr__(self):
        return "Score('{}')".format(str(self))

    def __eq__(self, other):
        if not isinstance(other, Score):
            other = Score(other)
        return True if self.value == other.value else False

    def __gt__(self, other):
        if not isinstance(other, Score):
            other = Score(other)
        return True if self.value > other.value else False

    def __le__(self, other):
        if not isinstance(other, Score):
            other = Score(other)
        return True if self.value <= other.value else False

    def get_grade(self):
        for grade in self.grading:
            low = grade[0]
            high = grade[1]
            if self > low and self <= high:
                return grade[2], grade[3]
        raise RuntimeError("Value is outside grading boundaries")


def compose_body(body_file, score):
    gradenum, gradetxt = score.get_grade()
    with open(body_file) as fp:
        body = fp.read()
    body = body.replace('@SCORE@', "%.1f" % score)
    body = body.replace('@GRADENUM@', gradenum)
    body = body.replace('@GRADETXT@', gradetxt)
    if gradenum == "2.0":
        epilogue = "Życzę powodzenia na poprawie,"
    else:
        epilogue = "Gratuluję,"
    body = body.replace('@EPILOGUE@', epilogue)
    return body


def get_results(filename):
    results = {}
    with open(filename) as fp:
        reader = csv.reader(fp, delimiter=';')
        for row in reader:
            student_id = row[0]
            score = row[1]
            if score in (None, ""):
                score = 0
            results[student_id] = Score(score)
    return results


MType = namedtuple('MType', ['type', 'encoding', 'maintype', 'subtype'])


class Message(MIMEMultipart):

    def __init__(self, fromaddr, toaddr, subject, bodyplain=None,
                 bodyhtml=None, attachments=[]):

        super(Message, self).__init__()
        self['Subject'] = subject
        self['From'] = fromaddr
        if isinstance(toaddr, str):
            toaddr = [toaddr]
        self['To'] = ", ".join(toaddr)
        self.preamble = 'This is a multi-part message in MIME format.'

        attachment_types = {}
        for att in attachments:
            ctype, encoding = mimetypes.guess_type(att)
            if ctype is None:
                raise RuntimeError("Could not guess the MIME type")
            maintype, subtype = ctype.split('/', 1)
            attachment_types[att] = MType(ctype, encoding, maintype, subtype)

        if bodyplain:
            text = MIMEText(bodyplain, _subtype='plain', _charset='UTF-8')

        if bodyhtml:
            image_cid = {}
            idx = 0
            for aname, atypes in attachment_types.items():
                if atypes.maintype != 'image': continue
                cid = "image{}".format(idx)
                idx += 1
                pattern = 'src\s*=\s*"{}"'.format(aname)
                substitute = 'src="cid:{}"'.format(cid)
                bodyhtml = re.sub(pattern, substitute, bodyhtml,
                                  re.IGNORECASE|re.MULTILINE)
                image_cid[aname] = cid
            html = MIMEText(bodyhtml, _subtype='html', _charset='UTF-8')

        if bodyplain and bodyhtml:
            alternative = MIMEMultipart('alternative')
            alternative.attach(text)
            alternative.attach(html)
            self.attach(alternative)
        elif bodyplain:
            self.attach(text)
        elif bodyhtml:
            self.attach(html)
        else:
            raise RuntimeError("plain text or html message must be present")

        for atname,attype in attachment_types.items():
            if attype.maintype == 'image':
                with open(atname, 'rb') as atfile:
                    atm = MIMEImage(atfile.read(), _subtype=attype.subtype)
                    if atname in image_cid:
                        cid = image_cid[atname]
                        atm.add_header('Content-ID', '<{}>'.format(cid))
            elif attype.maintype == 'text':
                with open(att) as atfile:
                    atm = MIMEText(atfile.read(), _subtype=attype.subtype)
            else:
                raise NotImplementedError(
                    "{} attachments are not implemented".format(attype.ctype))
            atm.add_header('Content-Disposition', 'attachment',
                           filename=atname)
            self.attach(atm)


class Sender(object):

    def __init__(self, server, user, password, dry_run=False):

        self.dry_run = dry_run
        self.server = server
        self.user = user
        self.password = password

    def __enter__(self):
        if not self.dry_run:
            self.smtp = smtplib.SMTP(self.server, 587)
            self.smtp.ehlo()
            self.smtp.starttls()
            self.smtp.login(self.user, self.password)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not self.dry_run:
            self.smtp.quit()

    def send(self, msg):
        """Actually send the message or return text if dry run"""
        if not dryRun:
            self.smtp.send_message(msg)
        else:
            return msg.as_string()


if __name__ == '__main__':

    mailPassword = getpass.getpass("Enter mailbox password:")

    results = get_results(testResults)

    with Sender(mailServer, mailUser, mailPassword, dryRun) as snd:
        for student, score in results.items():
            body = compose_body(fileBody, score)
            to = "%s@student.pwr.edu.pl" % student
            print("Sending score", score, "to", to)
            msg = Message(emailFrom, to, emailSubject, body,
                          attachments=[fileAttach])
            snd.send(msg)
            # let the mail server take a breath
            sleep(2)
