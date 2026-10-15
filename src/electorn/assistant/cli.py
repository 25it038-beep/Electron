"""Typer CLI command group for Electorn Advanced Personal Assistant."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import typer

from electorn.assistant.calling import TwilioTelephonyProvider
from electorn.assistant.schema import ActionStatus, PermissionMode, TaskPriority, TaskStatus, WritingStyle
from electorn.assistant.service import AssistantMonitorService
from electorn.assistant.supervisor import AssistantSupervisor

assistant_app = typer.Typer(
    name="assistant",
    help="Autonomous Personal Communication Agent for Email, WhatsApp, Files, Calls & Tasks.",
    no_args_is_help=True,
)

email_app = typer.Typer(name="email", help="Gmail OAuth 2.0 and inbox synchronization.")
whatsapp_app = typer.Typer(name="whatsapp", help="WhatsApp Business Platform integration.")
reply_app = typer.Typer(name="reply", help="Natural AI reply generation & approval.")
files_app = typer.Typer(name="files", help="File intelligence, attachment ingestion, & comparisons.")
calls_app = typer.Typer(name="calls", help="Telephony briefings, outbound calls, & transcripts.")
tasks_app = typer.Typer(name="tasks", help="Task tracking, priorities, & daily digests.")

assistant_app.add_typer(email_app)
assistant_app.add_typer(whatsapp_app)
assistant_app.add_typer(reply_app)
assistant_app.add_typer(files_app)
assistant_app.add_typer(calls_app)
assistant_app.add_typer(tasks_app)

console = Console()
_global_service: Optional[AssistantMonitorService] = None


def get_supervisor() -> AssistantSupervisor:
    return AssistantSupervisor()


# =============================================================================
# TOP-LEVEL ASSISTANT CONTROLS
# =============================================================================

@assistant_app.command(name="status")
def status_cmd() -> None:
    """Show live status of Personal Assistant, channels, and pending approvals."""
    sup = get_supervisor()
    st = sup.get_status()

    table = Table(title="⚡ Electorn Personal AI Assistant — Status", show_header=True)
    table.add_column("Property", style="bold cyan")
    table.add_column("Current Setting / Value", style="white")

    table.add_row("Permission Mode", f"[bold green]{st['permission_mode'].upper()}[/bold green]")
    table.add_row("System Paused", "[bold red]YES (All actions suspended)[/bold red]" if st["is_paused"] else "[bold green]NO (Active)[/bold green]")
    table.add_row("Default Writing Style", st["default_writing_style"].capitalize())
    table.add_row("Gmail Integration", "[bold green]Connected[/bold green]" if st["integrations"]["gmail"] == "connected" else "[yellow]Disconnected[/yellow]")
    table.add_row("WhatsApp Integration", "[bold green]Configured[/bold green]" if st["integrations"]["whatsapp"] == "configured" else "[dim]Not Configured[/dim]")
    table.add_row("Telephony Provider", st["integrations"]["telephony"].capitalize())
    table.add_row("Stored Messages", str(st["stats"]["total_stored_messages"]))
    table.add_row("Pending Approvals", f"[bold yellow]{st['stats']['pending_approvals']}[/bold yellow]")
    table.add_row("Active Tasks", str(st["stats"]["active_tasks"]))

    console.print(table)


@assistant_app.command(name="pause")
def pause_cmd() -> None:
    """Emergency killswitch: pause all assistant actions and monitoring."""
    sup = get_supervisor()
    msg = sup.pause()
    console.print(f"[bold yellow]⏸️  {msg}[/bold yellow]")


@assistant_app.command(name="resume")
def resume_cmd() -> None:
    """Resume assistant monitoring and operations."""
    sup = get_supervisor()
    msg = sup.resume()
    console.print(f"[bold green]▶️  {msg}[/bold green]")


@assistant_app.command(name="permissions")
def permissions_cmd(
    mode: Optional[str] = typer.Argument(None, help="Switch mode: 'observe', 'assist', 'controlled'")
) -> None:
    """Inspect or update the operational permission mode."""
    sup = get_supervisor()
    if mode:
        msg = sup.set_mode(mode)
        console.print(f"🔒 [bold green]{msg}[/bold green]")
    else:
        curr = sup.assistant_cfg.permission_mode.value
        console.print(Panel(
            f"Active Mode: [bold cyan]{curr.upper()}[/bold cyan]\n\n"
            f"• [bold]observe[/bold]: Read-only. Summarize messages, extract tasks, analyze files. Zero outbound actions.\n"
            f"• [bold]assist[/bold]: Prepares drafts and calls, but REQUIRES explicit human confirmation before sending.\n"
            f"• [bold]controlled[/bold]: Permits approved pre-whitelisted actions with full audit logging and killswitch.\n\n"
            f"To switch mode: [bold green]electorn assistant permissions <mode>[/bold green]",
            title="Permission & Safety System",
            border_style="cyan"
        ))


@assistant_app.command(name="digest")
def digest_cmd() -> None:
    """Generate daily communication and task digest."""
    sup = get_supervisor()
    tasks = sup.storage.list_tasks(status=TaskStatus.PENDING)
    digest = sup.task_engine.generate_daily_digest(tasks)

    panel_text = (
        f"📅 [bold white]Personal Communications & Task Digest[/bold white]\n\n"
        f"Total Pending Tasks: [bold cyan]{digest['total_pending']}[/bold cyan] "
        f"(🚨 Critical: {digest['critical_count']} | ⚠️ High: {digest['high_count']})\n\n"
    )
    if digest["critical_tasks"]:
        panel_text += "[bold red]Critical Actions Needed:[/bold red]\n" + "\n".join([f"  • {t}" for t in digest["critical_tasks"]]) + "\n\n"
    if digest["high_tasks"]:
        panel_text += "[bold yellow]High Priority:[/bold yellow]\n" + "\n".join([f"  • {t}" for t in digest["high_tasks"]]) + "\n\n"
    if digest["upcoming_tasks"]:
        panel_text += "[bold green]Upcoming:[/bold green]\n" + "\n".join([f"  • {t}" for t in digest["upcoming_tasks"]])

    console.print(Panel(panel_text, border_style="cyan"))


@assistant_app.command(name="activity")
def activity_cmd(limit: int = typer.Option(20, "--limit", "-n")) -> None:
    """View recent immutable audit logs."""
    sup = get_supervisor()
    logs = sup.permissions.get_recent_audit_logs(limit=limit)
    if not logs:
        console.print("[dim]No audit activity recorded yet.[/dim]")
        return

    table = Table(title="📜 Audit & Activity Log", show_header=True)
    table.add_column("Timestamp", style="dim")
    table.add_column("Event Type", style="bold cyan")
    table.add_column("Status", style="green")
    table.add_column("Details", style="white")

    for l in logs:
        st_style = "green" if l.get("status") == "success" else "red"
        table.add_row(
            l.get("timestamp", "")[:19],
            l.get("event_type", ""),
            f"[{st_style}]{l.get('status')}[/{st_style}]",
            json.dumps(l.get("details", {}))[:60],
        )
    console.print(table)


# =============================================================================
# EMAIL COMMANDS
# =============================================================================

@email_app.command(name="status")
def email_status() -> None:
    """Check Gmail connector authorization state."""
    sup = get_supervisor()
    if sup.email_connector.is_connected():
        console.print("✔ [bold green]Gmail connector is connected and authorized.[/bold green]")
    else:
        console.print("❌ [yellow]Gmail connector is not connected. Run 'electorn assistant email connect'[/yellow]")


@email_app.command(name="connect")
def email_connect(
    client_id: Optional[str] = typer.Option(None, "--client-id", help="Google Cloud OAuth Client ID"),
    code: Optional[str] = typer.Option(None, "--code", help="Authorization code from Google OAuth redirect"),
    client_secret: Optional[str] = typer.Option(None, "--client-secret", help="Google Cloud OAuth Client Secret"),
) -> None:
    """Initiate or complete official Google OAuth 2.0 authorization."""
    sup = get_supervisor()
    if not code:
        cid = client_id or "YOUR_GOOGLE_CLIENT_ID"
        auth_url = sup.email_connector.get_auth_url(cid)
        console.print(Panel(
            f"1. Create a project in [link=https://console.cloud.google.com]Google Cloud Console[/link].\n"
            f"2. Enable Gmail API.\n"
            f"3. Create OAuth 2.0 Credentials (Desktop or Web App).\n"
            f"4. Visit the authorization link below in your browser:\n\n"
            f"[bold cyan]{auth_url}[/bold cyan]\n\n"
            f"5. Paste the callback code here with:\n"
            f"[bold green]electorn assistant email connect --code <code> --client-id <id> --client-secret <secret>[/bold green]",
            title="Gmail OAuth 2.0 Setup",
            border_style="green"
        ))
    else:
        if not client_id or not client_secret:
            console.print("[bold red]Please provide both --client-id and --client-secret to complete code exchange.[/bold red]")
            return
        try:
            sup.email_connector.exchange_code(code, client_id, client_secret)
            console.print("✔ [bold green]Gmail OAuth tokens safely saved and connected![/bold green]")
        except Exception as e:
            console.print(f"[bold red]Authorization failed: {e}[/bold red]")


@email_app.command(name="sync")
def email_sync(
    query: str = typer.Option("label:INBOX", "--query", "-q"),
    limit: int = typer.Option(10, "--limit", "-n")
) -> None:
    """Fetch recent messages, index threads, and extract actionable tasks."""
    sup = get_supervisor()
    records = sup.sync_email(query=query, max_count=limit)
    console.print(f"✔ [bold green]Synchronized {len(records)} message(s) from Gmail.[/bold green]")


@email_app.command(name="search")
def email_search(query: str = typer.Argument(..., help="Search term")) -> None:
    """Search locally stored email messages."""
    sup = get_supervisor()
    all_msgs = sup.storage.list_messages(channel=ChannelType.GMAIL, limit=200)
    matches = [m for m in all_msgs if query.lower() in (m.subject or "").lower() or query.lower() in m.body_text.lower() or query.lower() in m.sender.lower()]

    if not matches:
        console.print(f"[dim]No messages matching '{query}' found.[/dim]")
        return

    table = Table(title=f"Email Search Results for '{query}'", show_header=True)
    table.add_column("ID", style="dim")
    table.add_column("Sender", style="bold cyan")
    table.add_column("Subject", style="white")
    table.add_column("Date", style="dim")

    for m in matches:
        table.add_row(m.message_id, m.sender[:30], (m.subject or "")[:40], str(m.timestamp)[:10])
    console.print(table)


@email_app.command(name="disconnect")
def email_disconnect() -> None:
    """Safely revoke and purge stored Gmail credentials."""
    sup = get_supervisor()
    sup.email_connector.disconnect()
    console.print("✔ [yellow]Gmail credentials purged.[/yellow]")


# =============================================================================
# WHATSAPP COMMANDS
# =============================================================================

@whatsapp_app.command(name="status")
def wa_status() -> None:
    """Display WhatsApp Business Cloud API configuration status."""
    sup = get_supervisor()
    if sup.whatsapp_connector.is_configured():
        console.print("✔ [bold green]WhatsApp Cloud API configured and ready.[/bold green]")
    else:
        console.print("[yellow]WhatsApp Cloud API not configured. Run 'electorn assistant whatsapp setup'[/yellow]")


@whatsapp_app.command(name="setup")
def wa_setup() -> None:
    """Explain WhatsApp setup instructions, webhook verification, and limitations."""
    console.print(Panel(
        "⚡ [bold cyan]Meta WhatsApp Business Cloud API Integration[/bold cyan]\n\n"
        "Official enterprise setup instructions:\n"
        "1. Create a Meta Developer App at [link=https://developers.facebook.com]developers.facebook.com[/link].\n"
        "2. Add the WhatsApp product to your app.\n"
        "3. Configure your webhook URL and Verify Token in Meta Dashboard.\n"
        "4. Set environment variables in your PowerShell environment:\n"
        "   $env:WHATSAPP_PHONE_NUMBER_ID = '<Phone Number ID>'\n"
        "   $env:WHATSAPP_ACCESS_TOKEN = '<Permanent System User Token>'\n"
        "   $env:WHATSAPP_APP_SECRET = '<App Secret for HMAC SHA256 validation>'\n\n"
        "⚠️  [bold yellow]Privacy & Platform Disclosures:[/bold yellow]\n"
        "• Electorn uses ONLY official authenticated WhatsApp Cloud APIs.\n"
        "• It does NOT scrape private sessions, steal web cookies, or violate Meta terms.",
        title="WhatsApp Integration Setup",
        border_style="green"
    ))


@whatsapp_app.command(name="sync")
def wa_sync() -> None:
    """Fetch stored WhatsApp messages."""
    sup = get_supervisor()
    msgs = sup.storage.list_messages(channel=ChannelType.WHATSAPP, limit=20)
    if not msgs:
        console.print("[dim]No WhatsApp messages received through webhooks yet.[/dim]")
        return
    for m in msgs:
        console.print(f"💬 [bold green]{m.sender}[/bold green]: {m.body_text}")


# =============================================================================
# REPLY COMMANDS (DRAFT / APPROVE / REJECT)
# =============================================================================

@reply_app.command(name="draft")
def reply_draft(
    message_id: str = typer.Argument(..., help="Source Message ID to draft reply for"),
    style: Optional[str] = typer.Option(None, "--style", "-s", help="Writing style: professional, friendly, concise, formal")
) -> None:
    """Draft a natural, context-aware reply for human review."""
    sup = get_supervisor()
    action = sup.draft_reply(message_id, style_override=style)

    console.print(Panel(
        f"Action ID: [bold cyan]{action.action_id}[/bold cyan]\n"
        f"Channel: [bold green]{action.channel.value.upper()}[/bold green]\n"
        f"Recipient: [bold white]{action.recipient}[/bold white]\n"
        f"Subject: [bold white]{action.subject}[/bold white]\n\n"
        f"[italic white]{action.content}[/italic white]\n\n"
        f"Status: [bold yellow]PENDING APPROVAL[/bold yellow]\n"
        f"To send: [bold green]electorn assistant reply approve {action.action_id}[/bold green]\n"
        f"To reject: [bold red]electorn assistant reply reject {action.action_id}[/bold red]",
        title="Draft Reply Review",
        border_style="yellow"
    ))


@reply_app.command(name="approve")
def reply_approve(action_id: str = typer.Argument(..., help="Action ID to approve and send")) -> None:
    """Authorize and execute a drafted outgoing message."""
    sup = get_supervisor()
    try:
        res = sup.approve_action(action_id)
        console.print(f"✔ [bold green]Action '{action_id}' approved and dispatched successfully![/bold green]")
        console.print(f"Details: {res['action']['execution_result']}")
    except Exception as e:
        console.print(f"❌ [bold red]Approval execution failed: {e}[/bold red]")


@reply_app.command(name="reject")
def reply_reject(
    action_id: str = typer.Argument(..., help="Action ID to reject"),
    reason: str = typer.Option("User cancelled", "--reason", "-r")
) -> None:
    """Reject and cancel a pending message draft."""
    sup = get_supervisor()
    try:
        sup.reject_action(action_id, reason=reason)
        console.print(f"✔ [yellow]Action '{action_id}' rejected and cancelled.[/yellow]")
    except Exception as e:
        console.print(f"❌ [bold red]Reject failed: {e}[/bold red]")


# =============================================================================
# FILES COMMANDS
# =============================================================================

@files_app.command(name="list")
def files_list() -> None:
    """List downloaded attachment files."""
    sup = get_supervisor()
    d = Path(sup.assistant_cfg.downloads_directory)
    if not d.exists() or not list(d.iterdir()):
        console.print(f"[dim]No downloaded files in {d}[/dim]")
        return
    table = Table(title="📂 Downloaded Attachments & Files", show_header=True)
    table.add_column("Filename", style="bold cyan")
    table.add_column("Size (KB)", style="white")
    table.add_column("Path", style="dim")
    for f in d.iterdir():
        if f.is_file():
            table.add_row(f.name, str(round(f.stat().st_size / 1024, 1)), str(f))
    console.print(table)


@files_app.command(name="analyze")
def files_analyze(file_path: str = typer.Argument(..., help="Local file path to analyze")) -> None:
    """Perform deep analysis of a document (PDF, DOCX, XLSX, CSV, Code, Images)."""
    sup = get_supervisor()
    try:
        rep = sup.analyze_document(file_path)
        panel_text = (
            f"📄 [bold white]{Path(file_path).name}[/bold white] ({rep.detected_mime})\n\n"
            f"[bold cyan]Executive Summary:[/bold cyan]\n{rep.executive_summary}\n\n"
            f"[bold yellow]Key Findings:[/bold yellow]\n" + "\n".join([f"  • {k}" for k in rep.key_findings]) + "\n\n"
        )
        if rep.deadlines_and_actions:
            panel_text += "[bold green]Extracted Actions & Deadlines:[/bold green]\n" + "\n".join([f"  • {d}" for d in rep.deadlines_and_actions]) + "\n\n"
        if rep.limitations:
            panel_text += f"[bold dim]Limitations / Notice: {rep.limitations}[/bold dim]\n"

        console.print(Panel(panel_text, title="Document Intelligence Report", border_style="cyan"))
    except Exception as e:
        console.print(f"❌ [bold red]Analysis failed: {e}[/bold red]")


@files_app.command(name="compare")
def files_compare(
    file_a: str = typer.Argument(..., help="First document path"),
    file_b: str = typer.Argument(..., help="Second document path")
) -> None:
    """Compare two documents side-by-side."""
    sup = get_supervisor()
    try:
        res = sup.compare_documents(file_a, file_b)
        console.print(Panel(
            f"⚖️  [bold white]{res['comparison_summary']}[/bold white]\n\n"
            f"• [bold cyan]{res['file_a']['name']}[/bold cyan] ({res['file_a']['size_kb']} KB): {', '.join(res['file_a']['findings'])}\n"
            f"• [bold magenta]{res['file_b']['name']}[/bold magenta] ({res['file_b']['size_kb']} KB): {', '.join(res['file_b']['findings'])}",
            title="Document Comparison",
            border_style="green"
        ))
    except Exception as e:
        console.print(f"❌ [bold red]Comparison failed: {e}[/bold red]")


# =============================================================================
# CALLS COMMANDS
# =============================================================================

@calls_app.command(name="capabilities")
def calls_capabilities() -> None:
    """Display real capabilities of the configured telephony provider."""
    sup = get_supervisor()
    caps = sup.telephony.get_capabilities()

    table = Table(title="📞 Telephony & Call Agent Capabilities", show_header=True)
    table.add_column("Capability", style="bold cyan")
    table.add_column("Status / Details", style="white")

    for k, v in caps.items():
        table.add_row(k.replace("_", " ").capitalize(), str(v))
    console.print(table)


@calls_app.command(name="prepare")
def calls_prepare(
    contact: str = typer.Argument(..., help="Contact name"),
    phone: str = typer.Option("+1234567890", "--phone", "-p", help="Destination phone number"),
    purpose: str = typer.Option("Project alignment & scheduling", "--purpose", help="Call purpose"),
) -> None:
    """Prepare a structured call briefing dossier before placing a call."""
    sup = get_supervisor()
    briefing = sup.prepare_call(contact=contact, phone=phone, purpose=purpose)

    console.print(Panel(
        f"Briefing ID: [bold cyan]{briefing.briefing_id}[/bold cyan]\n"
        f"Contact: [bold white]{briefing.contact_name}[/bold white] ({briefing.phone_number})\n"
        f"Purpose: [bold white]{briefing.purpose}[/bold white]\n"
        f"Provider: [dim]{briefing.provider_name}[/dim]\n"
        f"Estimated Cost: [dim]{briefing.estimated_cost}[/dim]\n\n"
        f"[bold yellow]Proposed Opening (with mandatory AI disclosure):[/bold yellow]\n"
        f"\"{briefing.proposed_opening}\"\n\n"
        f"[bold cyan]Key Talking Points:[/bold cyan]\n" + "\n".join([f"  • {p}" for p in briefing.key_talking_points]) + "\n\n"
        f"To initiate call: [bold green]electorn assistant calls start {briefing.briefing_id}[/bold green]",
        title="Outbound Call Briefing",
        border_style="cyan"
    ))


@calls_app.command(name="start")
def calls_start(briefing_id: str = typer.Argument(..., help="Briefing ID to initiate")) -> None:
    """Initiate approved call through telephony gateway."""
    sup = get_supervisor()
    briefing = sup.prepare_call("Client", "+1234567890", "Briefing review")
    rec = sup.start_call(briefing)

    tag = "[bold yellow][SIMULATED CALL][/bold yellow]" if rec.is_simulated else "[bold green][LIVE PSTN CALL][/bold green]"
    console.print(Panel(
        f"{tag} Status: [bold cyan]{rec.status.upper()}[/bold cyan]\n"
        f"Call ID: [dim]{rec.call_id}[/dim]\n"
        f"Duration: {rec.duration_seconds} seconds\n\n"
        f"[bold yellow]Call Summary:[/bold yellow]\n{rec.call_summary}\n\n"
        f"[bold cyan]Transcript:[/bold cyan]\n{rec.transcript}",
        title="Call Execution Result",
        border_style="green"
    ))


# =============================================================================
# TASKS COMMANDS
# =============================================================================

@tasks_app.command(name="list")
def tasks_list(status: Optional[str] = typer.Option(None, "--status", "-s")) -> None:
    """List actionable tasks extracted from messages, files, and calls."""
    sup = get_supervisor()
    t_status = TaskStatus(status.lower()) if status else None
    tasks = sup.storage.list_tasks(status=t_status)

    if not tasks:
        console.print("[dim]No tasks matching criteria found.[/dim]")
        return

    table = Table(title="✅ Personal Task Tracker", show_header=True)
    table.add_column("Task ID", style="dim")
    table.add_column("Priority", style="bold")
    table.add_column("Title", style="white")
    table.add_column("Deadline", style="yellow")
    table.add_column("Source", style="dim")
    table.add_column("Status", style="cyan")

    for t in tasks:
        pri_style = "red" if t.priority == TaskPriority.CRITICAL else ("yellow" if t.priority == TaskPriority.HIGH else "white")
        table.add_row(
            t.task_id,
            f"[{pri_style}]{t.priority.value.upper()}[/{pri_style}]",
            t.title[:45],
            t.deadline or "-",
            f"{t.source_type}:{t.source_id[:8]}",
            t.status.value,
        )
    console.print(table)


@tasks_app.command(name="complete")
def tasks_complete(task_id: str = typer.Argument(..., help="Task ID to mark complete")) -> None:
    """Mark an extracted task as completed."""
    sup = get_supervisor()
    task = sup.storage.get_task(task_id)
    if not task:
        console.print(f"[bold red]Task '{task_id}' not found.[/bold red]")
        return
    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.now(timezone.utc)
    sup.storage.save_task(task)
    console.print(f"✔ [bold green]Task '{task_id}' marked as completed![/bold green]")
