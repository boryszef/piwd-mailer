from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import mimetypes
import getpass
import smtplib
import csv
from time import sleep

# Global setup
testResults = "wyniki.csv"
emailFrom = "John Doe <john.doe@example.com>"
emailSubject = "Wyniki kolokwium z dnia X xxxxxxx XXXX"
fileBody = "email.txt"
fileAttach = "run.py"
mailServer = "xxxx.xxx.xxxx.pl"
mailUser = "borys.szefczyk"


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

    self.precision = 1

    self.grading = [
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
        return "{:.1f}".format(float(self.value))

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


def compose_email(emailFrom, emailTo, emailSubject, body,
                  attachment):
    msg = MIMEMultipart()
    msg['Subject'] = emailSubject
    msg['From'] = emailFrom
    msg['To'] = emailTo

    plain = MIMEText(body, 'plain')
    msg.attach(plain)

    ctype, encoding = mimetypes.guess_type(attachment)
    if ctype is None:
        raise RuntimeError("Could not guess the MIME type")
    maintype, subtype = ctype.split('/', 1)
    if maintype != 'text':
        raise NotImplementedError("Only text attachment are implemented")
    with open(attachment) as atm_file:
        atm = MIMEText(atm_file.read(), _subtype=subtype)
        atm.add_header('Content-Disposition', 'attachment',
                       filename=attachment)
        msg.attach(atm)
    return msg


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
                score = '0.0'
            results[student_id] = Score(score)
    return results


if __name__ == '__main__':
    mailPassword = getpass.getpass("Enter mailbox password:")
    results = get_results(testResults)
    srv = smtplib.SMTP(mailServer, 587)
    srv.ehlo()
    srv.starttls()
    srv.login(mailUser, mailPassword)
    for student, score in results.items():
        body = compose_body(fileBody, score)
        to = "%s@student.pwr.edu.pl" % student
        print("Sending score", score, "to", to)
        msg = compose_email(emailFrom, to, emailSubject, body, fileAttach)
        srv.send_message(msg)
        # let the mail server take a breath
        sleep(2)
    srv.quit()
