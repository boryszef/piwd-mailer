from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import mimetypes
import getpass
import smtplib
import csv
from time import sleep

# Global setup
testResults = "wyniki.csv"
emailFrom = "Xxxxx Xxxxxxxx <xxxxx.xxxxxxxx@xxx.xxx.xx>"
emailSubject = "Wyniki kolokwium z dnia X xxxxxxx XXXX"
fileBody = "email.txt"
fileAttach = "run.py"
mailServer = "xxxx.xxx.xxxx.pl"
mailUser = "borys.szefczyk"


grading = [
    (-3, 15, "2.0", "niedostateczny"),
    (15, 17.5, "3.0", "dostateczny"),
    (17.5, 20, "3.5", "dostateczny+"),
    (20, 22.5, "4.0", "dobry"),
    (22.5, 25, "4.5", "dobry+"),
    (25, 27.5, "5.0", "bardzo dobry"),
    (27.5, 30, "5.5", "celujący"),
]


def get_grade(score):
    for grade in grading:
        if score > grade[0] and score <= grade[1]:
            return grade[2], grade[3]
    return None


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
    gradenum, gradetxt = get_grade(score)
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
                score = 0.0
            else:
                score = float(score)
            results[student_id] = score
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
