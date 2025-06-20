#!/usr/bin/env python3
"""
Script to clean up duplicate analytics entries and reset counts.
This will help fix the inflated visit counts.
"""

import psycopg2
from psycopg2 import extras
import sys
import os

# Add the parent directory to the path so we can import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS

def get_pg_connection():
    """Return a new psycopg2 connection."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            connect_timeout=10
        )
        return conn
    except psycopg2.Error as e:
        print(f"[!] Database connection error: {e}")
        raise

def show_current_stats():
    """Show current analytics statistics."""
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Total entries
        cur.execute("SELECT COUNT(*) FROM site_analytics")
        total_entries = cur.fetchone()[0]
        
        # Entries by day
        cur.execute("""
            SELECT DATE(visit_time) as date, COUNT(*) as count
            FROM site_analytics
            WHERE visit_time >= NOW() - INTERVAL '7 days'
            GROUP BY DATE(visit_time)
            ORDER BY date DESC
        """)
        daily_counts = cur.fetchall()
        
        # Unique IPs
        cur.execute("SELECT COUNT(DISTINCT ip_address) FROM site_analytics")
        unique_ips = cur.fetchone()[0]
        
        # Unique users
        cur.execute("SELECT COUNT(DISTINCT user_id) FROM site_analytics WHERE user_id IS NOT NULL")
        unique_users = cur.fetchone()[0]
        
        print(f"\n[*] Current Analytics Statistics:")
        print(f"    Total entries: {total_entries}")
        print(f"    Unique IP addresses: {unique_ips}")
        print(f"    Unique registered users: {unique_users}")
        
        print(f"\n[*] Daily entry counts (last 7 days):")
        for date, count in daily_counts:
            print(f"    {date}: {count} entries")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"[!] Error showing stats: {e}")

def cleanup_duplicates():
    """Remove duplicate analytics entries."""
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        
        print("[*] Analyzing duplicate entries...")
        
        # Find duplicates (same IP, user, page, and day)
        cur.execute("""
            SELECT 
                COALESCE(user_id, -1) as user_key,
                ip_address,
                page_path,
                DATE(visit_time) as visit_date,
                COUNT(*) as duplicate_count
            FROM site_analytics
            GROUP BY COALESCE(user_id, -1), ip_address, page_path, DATE(visit_time)
            HAVING COUNT(*) > 1
            ORDER BY duplicate_count DESC
        """)
        
        duplicates = cur.fetchall()
        
        if not duplicates:
            print("[*] No duplicates found!")
            return 0
        
        print(f"[*] Found {len(duplicates)} groups of duplicates:")
        total_duplicates = sum(count - 1 for _, _, _, _, count in duplicates)
        print(f"[*] Total duplicate entries to remove: {total_duplicates}")
        
        # Show some examples
        print(f"\n[*] Top 5 duplicate groups:")
        for i, (user_key, ip, page, date, count) in enumerate(duplicates[:5]):
            user_display = "Anonymous" if user_key == -1 else f"User {user_key}"
            print(f"    {i+1}. {user_display} | {ip} | {page} | {date} | {count} entries")
        
        # Ask for confirmation
        response = input(f"\n[?] Remove {total_duplicates} duplicate entries? (y/N): ")
        if response.lower() != 'y':
            print("[*] Cleanup cancelled")
            return 0
        
        # Remove duplicates (keep the latest entry for each group)
        print("[*] Removing duplicates...")
        cur.execute("""
            DELETE FROM site_analytics 
            WHERE id NOT IN (
                SELECT DISTINCT ON (
                    COALESCE(user_id, -1), 
                    ip_address, 
                    page_path, 
                    DATE(visit_time)
                ) id
                FROM site_analytics
                ORDER BY 
                    COALESCE(user_id, -1), 
                    ip_address, 
                    page_path, 
                    DATE(visit_time), 
                    visit_time DESC
            )
        """)
        
        deleted_count = cur.rowcount
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"[✓] Successfully removed {deleted_count} duplicate entries")
        return deleted_count
        
    except Exception as e:
        print(f"[!] Error during cleanup: {e}")
        return 0

def reset_analytics():
    """Completely reset analytics data."""
    try:
        conn = get_pg_connection()
        cur = conn.cursor()
        
        # Count current entries
        cur.execute("SELECT COUNT(*) FROM site_analytics")
        total_entries = cur.fetchone()[0]
        
        print(f"[!] WARNING: This will delete ALL {total_entries} analytics entries!")
        response = input("[?] Are you sure you want to reset all analytics? (y/N): ")
        
        if response.lower() != 'y':
            print("[*] Reset cancelled")
            return False
        
        # Double confirmation
        response2 = input("[?] This cannot be undone. Type 'DELETE ALL' to confirm: ")
        if response2 != 'DELETE ALL':
            print("[*] Reset cancelled")
            return False
        
        # Delete all analytics data
        cur.execute("DELETE FROM site_analytics")
        deleted_count = cur.rowcount
        
        # Reset the sequence
        cur.execute("ALTER SEQUENCE site_analytics_id_seq RESTART WITH 1")
        
        conn.commit()
        cur.close()
        conn.close()
        
        print(f"[✓] Successfully deleted all {deleted_count} analytics entries")
        print("[✓] Analytics sequence reset")
        return True
        
    except Exception as e:
        print(f"[!] Error during reset: {e}")
        return False

def main():
    print("=" * 60)
    print("ANALYTICS CLEANUP TOOL")
    print("=" * 60)
    
    # Show current stats
    show_current_stats()
    
    print(f"\n[*] Cleanup Options:")
    print("  1. Remove duplicate entries (recommended)")
    print("  2. Reset all analytics data")
    print("  3. Show stats only")
    print("  4. Exit")
    
    try:
        choice = input("\n[?] Choose an option (1-4): ").strip()
        
        if choice == '1':
            print(f"\n[*] Starting duplicate cleanup...")
            deleted = cleanup_duplicates()
            if deleted > 0:
                print(f"\n[*] Updated statistics:")
                show_current_stats()
        
        elif choice == '2':
            print(f"\n[*] Starting full reset...")
            if reset_analytics():
                print(f"\n[*] Analytics reset complete")
                show_current_stats()
        
        elif choice == '3':
            print(f"\n[*] Current statistics shown above")
        
        elif choice == '4':
            print(f"[*] Exiting...")
        
        else:
            print(f"[!] Invalid choice: {choice}")
            
    except KeyboardInterrupt:
        print(f"\n[*] Cleanup cancelled by user")
    except Exception as e:
        print(f"[!] Error: {e}")

if __name__ == "__main__":
    main()
