import os


def send_price_drop(item_name: str, url: str, old_price: float, new_price: float):
    import boto3
    from botocore.exceptions import ClientError

    from_email = os.environ["SES_FROM_EMAIL"]
    to_email = os.environ["SES_TO_EMAIL"]
    region = os.environ.get("AWS_REGION", "ap-southeast-2")

    drop_pct = (old_price - new_price) / old_price * 100
    subject = f"Price drop: {item_name} is now ${new_price:.2f} ({drop_pct:.1f}% off)"

    body_html = f"""<html><body>
<h2>Price Drop Alert</h2>
<p><strong>{item_name}</strong></p>
<table>
  <tr><td>Was:</td><td><s>${old_price:.2f}</s></td></tr>
  <tr><td>Now:</td><td><strong>${new_price:.2f}</strong> &mdash; {drop_pct:.1f}% off</td></tr>
</table>
<p><a href="{url}">View item &rarr;</a></p>
</body></html>"""

    body_text = (
        f"{item_name}\n"
        f"Was: ${old_price:.2f}\n"
        f"Now: ${new_price:.2f}  ({drop_pct:.1f}% off)\n"
        f"{url}"
    )

    client = boto3.client("ses", region_name=region)
    try:
        client.send_email(
            Source=from_email,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": {
                    "Text": {"Data": body_text},
                    "Html": {"Data": body_html},
                },
            },
        )
        print(f"  Alert sent: {subject}")
    except ClientError as exc:
        print(f"  SES error: {exc.response['Error']['Message']}")
