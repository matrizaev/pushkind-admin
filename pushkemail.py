import imaplib
import email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import re

def GetPushkindEmails(EMAIL_IMAP, EMAIL_USER, EMAIL_PASS, seen = False):
	EMAIL_SEARCH_SUBJECT = 'новый заказ'
	if seen:
		EMAIL_SEARCH_PATTERN = 'SEEN'
	else:
		EMAIL_SEARCH_PATTERN = 'UNSEEN'
	imap = imaplib.IMAP4_SSL(EMAIL_IMAP)
	imap.login(EMAIL_USER, EMAIL_PASS)
	result = imap.select ('inbox')
	result, uidString = imap.uid('search', None, EMAIL_SEARCH_PATTERN)
	uidList = uidString[0].split()
	bodiesList = dict ()
	plainList = dict ()
	subjectsList = list ()
	discountsList = list ()
	for uid in uidList:
		result, emailRawData = imap.uid('fetch', uid, '(RFC822)')
		if result != 'OK':
			continue
		emailMessage = email.message_from_bytes(emailRawData[0][1])
		subject = email.header.decode_header(emailMessage['Subject'])
		if not subject[0][1] is None: 
			subject = subject[0][0].decode(subject[0][1])
		else:
			subject = subject[0][0]
		if EMAIL_SEARCH_SUBJECT not in subject:
			continue
		subjectsList.append (emailMessage['Subject'])
		for part in emailMessage.walk():
			if part.get_content_type() == 'text/html':
				body = part.get_payload(decode=True)
				bodiesList[uid] = body.decode(part.get_content_charset())
			elif part.get_content_type() == 'text/plain':
				plain = part.get_payload(decode=True)
				plain = plain.decode(part.get_content_charset())
				plainList[emailMessage['Subject']] = plain
	imap.close()
	imap.logout()
	return bodiesList, plainList
	
def GetEmailsDiscounts(plainBodies):
	discountsList = list()
	for plain in plainBodies:
		match = re.search ('(?:Купон\s+\([^)]+\)\s+-)(\d[\d\s]*(?:,\d+)?)', plain)
		if match:
			coupon = float(match.group(1).replace(' ', '').replace(',', '.'))
			match = re.search ('(?:Товары\s+)(\d[\d\s]*(?:,\d+)?)', plain)
			if match:
				totalCost = float(match.group(1).replace(' ', '').replace(',', '.'))
				discount = coupon / totalCost
				if discount > 1.0:
					discount = 1.0
			else:
				discount = 0.0
		else:
			discount = 0.0
		discountsList.append (discount)
	return discountsList
	
#
#Send new vendor-specific emails
#
def SendPushkindEmail (EMAIL_SMTP, EMAIL_USER, EMAIL_PASS, subject, recipients, html, csv = None):
	smtp = smtplib.SMTP_SSL (EMAIL_SMTP)
	smtp.login (EMAIL_USER, EMAIL_PASS)
	msg = MIMEMultipart('alternative')
	msg['Subject'] = subject
	msg['From'] = EMAIL_USER
	msg['To'] = ", ".join(recipients)
	part1 = MIMEText(re.sub('<[^<]+?>', '', html), 'plain')
	part2 = MIMEText(html, 'html')
	msg.attach(part1)
	msg.attach(part2)
	if csv:
		part3 = MIMEText(csv, _subtype = 'csv')
		part3['Content-Disposition'] = 'attachment; filename="{}"'.format(subject)
		msg.attach(part3)
	smtp.send_message(msg, msg['From'], recipients)
	smtp.quit()
	smtp.close()
	
def RemovePushkindEmails (EMAIL_IMAP, EMAIL_USER, EMAIL_PASS, uidList):
	imap = imaplib.IMAP4_SSL(EMAIL_IMAP)
	imap.login(EMAIL_USER, EMAIL_PASS)
	result = imap.select ('inbox')
	for uid in uidList:
		imap.uid('store', uid, '+FLAGS', '\\Deleted')
	imap.expunge()
	imap.close()
	imap.logout()
