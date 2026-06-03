import time
import requests
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.console import Console
from rich import box
from rich.text import Text

console = Console()
API_URL = "http://localhost:8000/stores/ST1008"


def generate_table():
    try:
        metrics_resp = requests.get(f"{API_URL}/metrics", timeout=2)
        funnel_resp = requests.get(f"{API_URL}/funnel", timeout=2)
        
        metrics = metrics_resp.json() if metrics_resp.ok else {}
        funnel = funnel_resp.json().get("funnel", []) if funnel_resp.ok else []
    except Exception:
        metrics = {}
        funnel = []

    # Create main layout
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=5),
        Layout(name="body")
    )
    
    # Header with purple branding
    header_text = Text()
    header_text.append("⚡ ", style="magenta bold")
    header_text.append("APEX RETAIL", style="magenta bold")
    header_text.append(" - Store Intelligence Dashboard", style="white dim")
    layout["header"].update(Panel(header_text, border_style="magenta", style="on #1a1a2e"))
    
    # Main body
    layout["body"].split_row(
        Layout(name="left"),
        Layout(name="right", ratio=1)
    )
    
    # === LEFT SIDE: METRICS ===
    metrics_layout = Layout()
    metrics_layout.split_column(
        Layout(name="m1"),
        Layout(name="m2"),
        Layout(name="m3"),
        Layout(name="m4")
    )
    
    visitors = str(metrics.get("unique_visitors", "--"))
    conversion = f"{metrics.get('conversion_rate', 0.0) * 100:.1f}%"
    queue = str(metrics.get("queue_depth", "--"))
    abandon = f"{metrics.get('abandonment_rate', 0.0) * 100:.1f}%"
    
    # Metric cards with colored borders
    m1_text = Text(visitors, style="bold magenta")
    metrics_layout["m1"].update(
        Panel(m1_text, title="👥 Unique Visitors", border_style="magenta", padding=(1, 2))
    )
    
    m2_text = Text(conversion, style="bold pink1")
    metrics_layout["m2"].update(
        Panel(m2_text, title="💰 Conversion Rate", border_style="pink1", padding=(1, 2))
    )
    
    m3_text = Text(queue, style="bold medium_purple1")
    metrics_layout["m3"].update(
        Panel(m3_text, title="📊 Queue Depth", border_style="medium_purple1", padding=(1, 2))
    )
    
    m4_text = Text(abandon, style="bold red")
    metrics_layout["m4"].update(
        Panel(m4_text, title="⚠️  Abandonment", border_style="red", padding=(1, 2))
    )
    
    layout["left"].update(Panel(metrics_layout, title="[bold magenta]Live Metrics[/bold magenta]", border_style="magenta"))
    
    # === RIGHT SIDE: FUNNEL & DWELL ===
    right_layout = Layout()
    right_layout.split_column(
        Layout(name="funnel", ratio=1.5),
        Layout(name="dwell", ratio=1.5)
    )
    
    # Funnel Table
    funnel_table = Table(box=box.ROUNDED, expand=True, padding=(0, 1))
    funnel_table.add_column("Stage", style="magenta bold", width=20)
    funnel_table.add_column("Count", justify="right", style="cyan", width=10)
    funnel_table.add_column("Drop %", justify="right", style="red", width=10)
    
    for stage in funnel:
        name = stage["stage"].replace("_", " ")
        count = str(stage["count"])
        drop = f"{stage['dropoff_percentage'] * 100:.1f}%" if stage["dropoff_percentage"] > 0 else "-"
        funnel_table.add_row(name, count, drop)
        
    right_layout["funnel"].update(Panel(funnel_table, title="[bold magenta]Conversion Funnel[/bold magenta]", border_style="magenta"))
    
    # Dwell Time Table
    dwell = metrics.get("avg_dwell_per_zone", {})
    dwell_table = Table(box=box.ROUNDED, expand=True, padding=(0, 1))
    dwell_table.add_column("Zone", style="medium_purple1 bold", width=20)
    dwell_table.add_column("Avg Dwell", justify="right", style="cyan", width=20)
    
    for zone, minutes in dwell.items():
        m = int(minutes)
        s = int((minutes - m) * 60)
        zone_name = zone.replace("_", " ")
        dwell_table.add_row(zone_name, f"{m}m {s}s")
        
    right_layout["dwell"].update(Panel(dwell_table, title="[bold medium_purple1]Dwell Times by Zone[/bold medium_purple1]", border_style="medium_purple1"))
    
    layout["right"].update(right_layout)
    
    return layout

if __name__ == "__main__":
    console.clear()
    with Live(generate_table(), refresh_per_second=2, screen=True) as live:
        try:
            for i in range(300):  # Run for ~150 seconds
                time.sleep(0.5)
                live.update(generate_table())
        except KeyboardInterrupt:
            console.print("[red]Dashboard stopped by user[/red]")

