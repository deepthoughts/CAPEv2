#!/usr/bin/env python
# Copyright (C) 2014-2016 Cuckoo Foundation.
# This file is part of Cuckoo Sandbox - http://www.cuckoosandbox.org
# See the file 'docs/LICENSE' for copying permission.

from __future__ import absolute_import
import argparse
import asyncore
import logging
import os
import smtplib
import sys
from datetime import datetime
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from smtpd import SMTPServer

# Cuckoo root
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), ".."))
from lib.cuckoo.common.config import Config

email_config = Config("smtp_sinkhole")


class SmtpSink(SMTPServer):
    """SMTP Sinkhole server."""

    # Where mails should be saved.
    mail_dir = None
    forward = None

    def process_message(self, peer, mailfrom, rcpttos, data):
        """Custom mail processing used to save mails to disk."""
        # Save message to disk only if path is passed.
        timestamp = datetime.now()
        if self.mail_dir:
            file_name = "%s" % timestamp.strftime("%Y%m%d%H%M%S")

            # Duplicate check.
            i = 0
            while os.path.exists(os.path.join(self.mail_dir, file_name + str(i))):
                i += 1

            file_name += str(i)
            with open(os.path.join(self.mail_dir, file_name), "w") as mail:
                mail.write(data)

        # Forward message to specific email address
        if self.forward and email_config:
            try:
                timestamp = datetime.now()
                msg = MIMEMultipart()
                msg["Subject"] = "Email from smtp sinkhole: {0}".format(timestamp.strftime("%Y-%m-%d %H:%M:%S"))
                msg["From"] = email_config.email["from"]
                msg["To"] = email_config.email["to"]
                part = MIMEBase("application", "octet-stream")
                part.set_payload(data)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", 'attachment; filename="cuckoo.eml"')
                msg.attach(part)
                server = smtplib.SMTP_SSL(email_config.email["server"], int(email_config.email["port"]))
                server.login(email_config.email["user"], email_config.email["password"])
                server.set_debuglevel(1)
                server.sendmail(email_config.email["from"], email_config.email["to"].split(" ,"), msg.as_string())
                server.quit()
            except Exception as e:
                logging.error(e)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="smtp_sinkhole.py", usage="%(prog)s [host [port]]", description="SMTP Sinkhole")
    parser.add_argument("host", nargs="?", default="127.0.0.1")
    parser.add_argument("port", nargs="?", type=int, default=1025)
    parser.add_argument("--dir", default=None, help="Directory used to dump emails.")
    parser.add_argument("--forward", action="store_true", default=False, help="Forward emails to specific email address")

    args = parser.parse_args()

    s = SmtpSink((args.host, args.port), None)
    s.mail_dir = args.dir
    s.forward = args.forward

    try:
        asyncore.loop()
    except KeyboardInterrupt:
        pass
