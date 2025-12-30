import os
from typing import List

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from dotenv import load_dotenv

load_dotenv()


def send_shortlist_email(to_email: str, daycares: List[dict], search_address: str) -> bool:
    """
    Send a shortlist email to the user via SendGrid.

    Args:
        to_email: Recipient email address
        daycares: List of daycare dictionaries with details
        search_address: The address the user searched from

    Returns:
        True if email sent successfully, False otherwise
    """
    api_key = os.getenv("SENDGRID_API_KEY")
    from_email = os.getenv("SENDGRID_FROM_EMAIL", "noreply@findmydaycare.com")

    if not api_key:
        print("SENDGRID_API_KEY not configured")
        return False

    # Build HTML email content
    html_content = _build_email_html(daycares, search_address)
    text_content = _build_email_text(daycares, search_address)

    message = Mail(
        from_email=Email(from_email, "Find My Daycare"),
        to_emails=To(to_email),
        subject="Your Find My Daycare Shortlist",
        plain_text_content=Content("text/plain", text_content),
        html_content=Content("text/html", html_content),
    )

    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        return response.status_code in (200, 201, 202)
    except Exception as e:
        print(f"SendGrid error: {e}")
        return False


def _build_email_html(daycares: List[dict], search_address: str) -> str:
    """Build HTML email content."""
    daycare_rows = ""
    for d in daycares:
        badges = ""
        if d.get("cwelcc"):
            badges += '<span style="background:#e8f4f8;color:#2e7d9a;padding:4px 8px;border-radius:4px;font-size:12px;margin-right:4px;">CWELCC</span>'
        if d.get("subsidy"):
            badges += '<span style="background:#e6f4f1;color:#0f7b6c;padding:4px 8px;border-radius:4px;font-size:12px;">Subsidy</span>'

        rating_html = ""
        if d.get("googleRating"):
            rating_html = f'<p style="margin:4px 0;color:#f59e0b;font-size:14px;">&#9733; {d["googleRating"]}'
            if d.get("googleReviewsCount"):
                rating_html += f' <span style="color:#6b6b6b;">({d["googleReviewsCount"]} reviews)</span>'
            rating_html += '</p>'

        website_html = ""
        if d.get("website"):
            website_html = f'<p style="margin:4px 0;"><a href="{d["website"]}" style="color:#2563eb;text-decoration:none;">Visit Website</a></p>'

        phone_html = ""
        if d.get("phone"):
            phone_html = f'<p style="margin:4px 0;"><a href="tel:{d["phone"]}" style="color:#37352f;text-decoration:none;">{d["phone"]}</a></p>'

        daycare_rows += f'''
        <tr>
            <td style="padding:20px;border-bottom:1px solid #e8e5e0;">
                <h3 style="margin:0 0 8px 0;color:#37352f;font-size:18px;">{d.get("name", "Unknown")}</h3>
                <p style="margin:4px 0;color:#6b6b6b;font-size:14px;">{d.get("address", "")}, {d.get("postalCode", "")}</p>
                <p style="margin:4px 0;color:#0f7b6c;font-weight:600;font-size:14px;">{d.get("distanceKm", "")} km away</p>
                {rating_html}
                {phone_html}
                {website_html}
                <p style="margin:8px 0 0 0;">{badges}</p>
            </td>
        </tr>
        '''

    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin:0;padding:0;background-color:#faf9f7;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#faf9f7;padding:40px 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color:#ffffff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.06);">
                        <tr>
                            <td style="padding:32px;text-align:center;border-bottom:1px solid #e8e5e0;">
                                <h1 style="margin:0;color:#37352f;font-size:24px;">Your Daycare Shortlist</h1>
                                <p style="margin:12px 0 0 0;color:#6b6b6b;font-size:14px;">
                                    {len(daycares)} daycares near {search_address}
                                </p>
                            </td>
                        </tr>
                        {daycare_rows}
                        <tr>
                            <td style="padding:24px;text-align:center;background-color:#f5f3f0;border-radius:0 0 12px 12px;">
                                <p style="margin:0;color:#6b6b6b;font-size:13px;">
                                    Sent from <a href="https://findmydaycare.com" style="color:#2e7d9a;text-decoration:none;">Find My Daycare</a>
                                </p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    '''


def _build_email_text(daycares: List[dict], search_address: str) -> str:
    """Build plain text email content."""
    lines = [
        "Your Daycare Shortlist",
        f"{len(daycares)} daycares near {search_address}",
        "",
        "=" * 40,
        "",
    ]

    for d in daycares:
        lines.append(d.get("name", "Unknown"))
        lines.append(f"  {d.get('address', '')}, {d.get('postalCode', '')}")
        lines.append(f"  {d.get('distanceKm', '')} km away")

        if d.get("phone"):
            lines.append(f"  Phone: {d['phone']}")
        if d.get("website"):
            lines.append(f"  Website: {d['website']}")
        if d.get("googleRating"):
            rating_text = f"  Rating: {d['googleRating']}"
            if d.get("googleReviewsCount"):
                rating_text += f" ({d['googleReviewsCount']} reviews)"
            lines.append(rating_text)

        badges = []
        if d.get("cwelcc"):
            badges.append("CWELCC")
        if d.get("subsidy"):
            badges.append("Subsidy")
        if badges:
            lines.append(f"  {', '.join(badges)}")

        lines.append("")

    lines.append("=" * 40)
    lines.append("Sent from Find My Daycare")

    return "\n".join(lines)
