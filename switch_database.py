"""
Quick switch between SQLite (fast local) and Neon (cloud) databases
"""

import sys
import os
from pathlib import Path

def read_env():
    """Read current .env file"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env file not found!")
        return None
    return env_file.read_text()

def write_env(content):
    """Write .env file"""
    env_file = Path(".env")
    env_file.write_text(content)
    print(f"✓ Updated {env_file.absolute()}")

def switch_to_sqlite():
    """Switch to SQLite database"""
    env_content = read_env()
    if not env_content:
        return
    
    # Comment out Neon DATABASE_URL
    lines = []
    neon_url = None
    for line in env_content.split('\n'):
        if line.startswith('DATABASE_URL=postgresql://'):
            neon_url = line
            lines.append(f'# {line}  # Neon (production)')
        elif line.startswith('# DATABASE_URL=postgresql://'):
            lines.append(line)  # Keep commented
        elif line.startswith('DATABASE_URL=sqlite://'):
            lines.append(line)  # Keep SQLite active
        elif line.startswith('# DATABASE_URL=sqlite://'):
            # Uncomment SQLite
            lines.append(line[2:].strip())
        else:
            lines.append(line)
    
    # Add SQLite URL if not present
    if not any('sqlite://' in line for line in lines):
        lines.append('\n# SQLite for local development (FAST)')
        lines.append('DATABASE_URL=sqlite:///./auction_db.sqlite')
    
    write_env('\n'.join(lines))
    print("\n✅ Switched to SQLite!")
    print("   → Instant queries (~10-50ms)")
    print("   → No network latency")
    print("   → Perfect for development\n")

def switch_to_neon():
    """Switch to Neon database"""
    env_content = read_env()
    if not env_content:
        return
    
    # Uncomment Neon DATABASE_URL, comment SQLite
    lines = []
    neon_found = False
    for line in env_content.split('\n'):
        if line.startswith('# DATABASE_URL=postgresql://'):
            # Uncomment Neon
            lines.append(line[2:].strip().replace('  # Neon (production)', ''))
            neon_found = True
        elif line.startswith('DATABASE_URL=postgresql://'):
            lines.append(line)  # Keep Neon active
            neon_found = True
        elif line.startswith('DATABASE_URL=sqlite://'):
            # Comment out SQLite
            lines.append(f'# {line}  # Local dev (fast)')
        elif line.startswith('# DATABASE_URL=sqlite://'):
            lines.append(line)  # Keep commented
        else:
            lines.append(line)
    
    if not neon_found:
        print("❌ No Neon DATABASE_URL found in .env file!")
        print("   Add your Neon connection string to .env first.")
        return
    
    write_env('\n'.join(lines))
    print("\n✅ Switched to Neon!")
    print("   → Cloud database (shared)")
    print("   → May have cold start (9s first query)")
    print("   → Keep-alive prevents sleep\n")

def show_status():
    """Show current database configuration"""
    env_content = read_env()
    if not env_content:
        return
    
    print("\n" + "="*70)
    print("CURRENT DATABASE CONFIGURATION")
    print("="*70 + "\n")
    
    for line in env_content.split('\n'):
        if 'DATABASE_URL' in line:
            if line.startswith('#'):
                print(f"  {line}")
            else:
                print(f"✓ {line}")
    
    # Detect active database
    if 'DATABASE_URL=sqlite://' in env_content and not '# DATABASE_URL=sqlite://' in env_content:
        print("\n📊 Active: SQLite (Local)")
        print("   → Fast queries (~10-50ms)")
        print("   → No cold starts")
    elif 'DATABASE_URL=postgresql://' in env_content and not '# DATABASE_URL=postgresql://' in env_content:
        print("\n📊 Active: Neon (Cloud)")
        print("   → May have cold start on first query")
        print("   → Keep-alive job prevents sleep")
    
    print("="*70 + "\n")

def main():
    if len(sys.argv) < 2:
        print("\nDatabase Switcher for Development\n")
        print("Usage:")
        print("  python switch_database.py sqlite   - Switch to SQLite (fast)")
        print("  python switch_database.py neon     - Switch to Neon (cloud)")
        print("  python switch_database.py status   - Show current config")
        print()
        show_status()
        return
    
    command = sys.argv[1].lower()
    
    if command == 'sqlite':
        switch_to_sqlite()
    elif command == 'neon':
        switch_to_neon()
    elif command == 'status':
        show_status()
    else:
        print(f"❌ Unknown command: {command}")
        print("   Use: sqlite, neon, or status")

if __name__ == "__main__":
    main()
