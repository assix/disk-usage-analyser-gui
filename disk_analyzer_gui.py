#!/usr/bin/env python3
"""
Disk Usage Analyzer - Native GUI Application
A lightweight, fast disk analyzer with visual interface
No external dependencies required - uses Python's built-in libraries
"""

import os
import sys
import json
import threading
import time
from pathlib import Path
from collections import defaultdict
import subprocess

# Try to import tkinter, fall back to terminal UI if not available
try:
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox
    HAVE_GUI = True
except ImportError:
    HAVE_GUI = False
    print("Warning: Tkinter not available. Please install: apt-get install python3-tk")
    print("Falling back to terminal mode...")


class DiskAnalyzer:
    """High-performance disk analyzer core"""
    
    def __init__(self):
        self.file_categories = {
            'video': {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp'},
            'image': {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff', '.raw', '.heic'},
            'pdf': {'.pdf'},
            'document': {'.doc', '.docx', '.txt', '.odt', '.rtf', '.tex', '.wpd', '.pages'},
            'archive': {'.zip', '.tar', '.gz', '.bz2', '.7z', '.rar', '.xz', '.tgz', '.deb', '.rpm'},
            'audio': {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus'},
            'code': {'.py', '.js', '.java', '.cpp', '.c', '.h', '.sh', '.rb', '.go', '.rs', '.php', '.html', '.css'},
        }
        self.cancel_flag = False
        self.current_results = {
            'total_size': 0,
            'file_count': 0,
            'dir_count': 0,
            'categories': defaultdict(int),
            'largest_files': [],
            'largest_dirs': [],
            'all_items': []
        }
        
    def format_bytes(self, bytes_val):
        """Convert bytes to human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024.0:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.2f} PB"
    
    def get_category(self, filepath):
        """Determine file category based on extension"""
        ext = Path(filepath).suffix.lower()
        for category, extensions in self.file_categories.items():
            if ext in extensions:
                return category
        return 'other'
    
    def scan_directory(self, root_path, progress_callback=None, update_callback=None, max_depth=None):
        """Scan directory and build analysis data with real-time updates"""
        self.cancel_flag = False
        self.current_results = {
            'total_size': 0,
            'file_count': 0,
            'dir_count': 0,
            'categories': defaultdict(int),
            'largest_files': [],
            'largest_dirs': [],
            'all_items': []
        }
        
        dir_sizes = {}
        update_counter = 0
        
        def scan_recursive(path, depth=0):
            nonlocal update_counter
            
            if self.cancel_flag:
                return 0
                
            if max_depth and depth > max_depth:
                return 0
                
            total_size = 0
            
            try:
                items = list(Path(path).iterdir())
                self.current_results['dir_count'] += 1
                
                for item in items:
                    if self.cancel_flag:
                        return total_size
                        
                    try:
                        if item.is_symlink():
                            continue
                            
                        if item.is_file():
                            size = item.stat().st_size
                            total_size += size
                            self.current_results['file_count'] += 1
                            self.current_results['total_size'] += size
                            
                            # Categorize
                            category = self.get_category(item)
                            self.current_results['categories'][category] += size
                            
                            # Store file info
                            file_info = {
                                'path': str(item),
                                'name': item.name,
                                'size': size,
                                'type': 'file',
                                'category': category
                            }
                            self.current_results['all_items'].append(file_info)
                            
                            # Real-time update every 50 items
                            update_counter += 1
                            if update_counter % 50 == 0 and update_callback:
                                update_callback(self.current_results.copy())
                            
                            if progress_callback:
                                progress_callback(self.current_results['file_count'], str(item))
                                
                        elif item.is_dir():
                            dir_size = scan_recursive(item, depth + 1)
                            total_size += dir_size
                            dir_sizes[str(item)] = dir_size
                            
                            # Add directory to results
                            dir_info = {
                                'path': str(item),
                                'name': item.name,
                                'size': dir_size,
                                'type': 'folder',
                                'category': 'folder'
                            }
                            self.current_results['all_items'].append(dir_info)
                            
                            # Update after each directory
                            if update_callback:
                                update_callback(self.current_results.copy())
                            
                    except (PermissionError, OSError):
                        continue
                        
            except (PermissionError, OSError):
                pass
                
            return total_size
        
        # Start scanning
        scan_recursive(root_path)
        
        # Final update
        if update_callback:
            update_callback(self.current_results.copy())
        
        return self.current_results


class DiskAnalyzerGUI:
    """GUI Application using Tkinter"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("Disk Usage Analyzer")
        self.root.geometry("1200x800")
        
        self.analyzer = DiskAnalyzer()
        self.current_results = None
        self.scanning = False
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the user interface"""
        
        # Style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Title
        title = ttk.Label(main_frame, text="🗄️ Disk Usage Analyzer", font=('Arial', 20, 'bold'))
        title.grid(row=0, column=0, columnspan=4, pady=10)
        
        # Control Panel
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding="10")
        control_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(control_frame, text="Path:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.path_var = tk.StringVar(value=str(Path.home()))
        path_entry = ttk.Entry(control_frame, textvariable=self.path_var, width=50)
        path_entry.grid(row=0, column=1, padx=5)
        
        ttk.Button(control_frame, text="Browse", command=self.browse_path).grid(row=0, column=2, padx=5)
        
        ttk.Label(control_frame, text="Max Depth:").grid(row=0, column=3, sticky=tk.W, padx=5)
        self.depth_var = tk.StringVar(value="All")
        depth_combo = ttk.Combobox(control_frame, textvariable=self.depth_var, width=10, 
                                   values=["All", "3", "5", "10", "15"])
        depth_combo.grid(row=0, column=4, padx=5)
        
        self.scan_btn = ttk.Button(control_frame, text="🔍 Scan Directory", command=self.start_scan)
        self.scan_btn.grid(row=0, column=5, padx=5)
        
        self.cancel_btn = ttk.Button(control_frame, text="⏹ Cancel", command=self.cancel_scan, state='disabled')
        self.cancel_btn.grid(row=0, column=6, padx=5)
        
        # Progress
        self.progress_var = tk.StringVar(value="Ready to scan")
        progress_label = ttk.Label(control_frame, textvariable=self.progress_var)
        progress_label.grid(row=1, column=0, columnspan=7, pady=5)
        
        self.progress_bar = ttk.Progressbar(control_frame, mode='indeterminate')
        self.progress_bar.grid(row=2, column=0, columnspan=7, sticky=(tk.W, tk.E), pady=5)
        
        # Stats Panel
        stats_frame = ttk.LabelFrame(main_frame, text="Statistics", padding="10")
        stats_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        
        self.stats_labels = {}
        stats_data = [
            ("Total Size:", "total_size"),
            ("Files:", "files"),
            ("Folders:", "folders"),
            ("Largest Item:", "largest")
        ]
        
        for i, (label_text, key) in enumerate(stats_data):
            ttk.Label(stats_frame, text=label_text, font=('Arial', 10, 'bold')).grid(row=0, column=i*2, padx=10, sticky=tk.W)
            self.stats_labels[key] = ttk.Label(stats_frame, text="—", font=('Arial', 12))
            self.stats_labels[key].grid(row=0, column=i*2+1, padx=10, sticky=tk.W)
        
        # Categories Panel with Pie Chart
        viz_frame = ttk.LabelFrame(main_frame, text="Storage Visualization", padding="10")
        viz_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        viz_frame.columnconfigure(0, weight=1)
        viz_frame.columnconfigure(1, weight=0)
        
        # Bar chart on left
        cat_frame = ttk.Frame(viz_frame)
        cat_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        ttk.Label(cat_frame, text="Category Breakdown", font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.category_canvas = tk.Canvas(cat_frame, height=200, bg='white')
        self.category_canvas.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        # Pie chart on right
        pie_frame = ttk.Frame(viz_frame)
        pie_frame.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        ttk.Label(pie_frame, text="Storage Distribution", font=('Arial', 10, 'bold')).grid(row=0, column=0, pady=(0, 5))
        self.pie_canvas = tk.Canvas(pie_frame, width=250, height=250, bg='white')
        self.pie_canvas.grid(row=1, column=0)
        
        # Filter Panel
        filter_frame = ttk.Frame(main_frame)
        filter_frame.grid(row=4, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(filter_frame, text="Show:").grid(row=0, column=0, padx=5)
        self.filter_var = tk.StringVar(value="all")
        ttk.Radiobutton(filter_frame, text="All Items", variable=self.filter_var, 
                       value="all", command=self.apply_filter).grid(row=0, column=1)
        ttk.Radiobutton(filter_frame, text="Files Only", variable=self.filter_var, 
                       value="files", command=self.apply_filter).grid(row=0, column=2)
        ttk.Radiobutton(filter_frame, text="Folders Only", variable=self.filter_var, 
                       value="folders", command=self.apply_filter).grid(row=0, column=3)
        
        ttk.Label(filter_frame, text="Sort:").grid(row=0, column=4, padx=(20, 5))
        self.sort_var = tk.StringVar(value="size")
        ttk.Radiobutton(filter_frame, text="By Size", variable=self.sort_var, 
                       value="size", command=self.apply_filter).grid(row=0, column=5)
        ttk.Radiobutton(filter_frame, text="By Name", variable=self.sort_var, 
                       value="name", command=self.apply_filter).grid(row=0, column=6)
        
        # Items Table
        table_frame = ttk.LabelFrame(main_frame, text="Items", padding="10")
        table_frame.grid(row=5, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        main_frame.rowconfigure(5, weight=1)
        
        # Create Treeview
        columns = ('Name', 'Type', 'Size', 'Path')
        self.tree = ttk.Treeview(table_frame, columns=columns, show='tree headings', height=15)
        
        self.tree.heading('#0', text='#')
        self.tree.column('#0', width=50)
        self.tree.heading('Name', text='Name')
        self.tree.column('Name', width=250)
        self.tree.heading('Type', text='Type')
        self.tree.column('Type', width=100)
        self.tree.heading('Size', text='Size')
        self.tree.column('Size', width=120)
        self.tree.heading('Path', text='Path')
        self.tree.column('Path', width=400)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        
        # Context menu
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Move to Trash", command=self.delete_selected)
        self.context_menu.add_command(label="Open in File Manager", command=self.open_in_filemanager)
        self.tree.bind("<Button-3>", self.show_context_menu)
        
        # Status Bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=6, column=0, columnspan=4, sticky=(tk.W, tk.E))
        
    def browse_path(self):
        """Open directory browser"""
        path = filedialog.askdirectory(initialdir=self.path_var.get())
        if path:
            self.path_var.set(path)
    
    def progress_callback(self, file_count, current_file):
        """Update progress during scan"""
        self.progress_var.set(f"Scanning... {file_count} files found - {Path(current_file).name}")
        self.root.update_idletasks()
    
    def start_scan(self):
        """Start directory scan in background thread"""
        if self.scanning:
            return
            
        path = self.path_var.get()
        if not Path(path).exists():
            messagebox.showerror("Error", "Path does not exist!")
            return
        
        self.scanning = True
        self.scan_btn.config(state='disabled')
        self.cancel_btn.config(state='normal')
        self.progress_bar.start(10)
        self.tree.delete(*self.tree.get_children())
        
        # Clear current results
        self.current_results = None
        
        # Get max depth
        depth_str = self.depth_var.get()
        max_depth = None if depth_str == "All" else int(depth_str)
        
        # Run scan in thread
        def scan_thread():
            try:
                self.current_results = self.analyzer.scan_directory(
                    path, 
                    progress_callback=self.progress_callback,
                    update_callback=self.realtime_update,
                    max_depth=max_depth
                )
                self.root.after(0, self.scan_complete)
            except Exception as e:
                self.root.after(0, lambda: self.scan_error(str(e)))
        
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def realtime_update(self, results):
        """Handle real-time updates during scanning"""
        def update_ui():
            # Update stats
            self.stats_labels['total_size'].config(
                text=self.analyzer.format_bytes(results['total_size']))
            self.stats_labels['files'].config(
                text=f"{results['file_count']:,}")
            self.stats_labels['folders'].config(
                text=f"{results['dir_count']:,}")
            
            # Update visualizations
            self.draw_categories(results)
            self.draw_pie_chart(results)
            
            # Update table with top items (limit to avoid slowdown)
            self.update_table_realtime(results)
        
        # Schedule UI update in main thread
        self.root.after(0, update_ui)
    
    def update_table_realtime(self, results):
        """Update table with current results during scan"""
        # Only update every few seconds to avoid slowdown
        current_time = time.time()
        if not hasattr(self, '_last_table_update'):
            self._last_table_update = 0
        
        if current_time - self._last_table_update < 1.0:  # Update max once per second
            return
        
        self._last_table_update = current_time
        
        # Get filter settings
        filter_type = self.filter_var.get()
        items = results['all_items'].copy()
        
        if filter_type == 'files':
            items = [x for x in items if x['type'] == 'file']
        elif filter_type == 'folders':
            items = [x for x in items if x['type'] == 'folder']
        
        # Sort by size
        items = sorted(items, key=lambda x: x['size'], reverse=True)[:100]  # Top 100 only during scan
        
        # Clear and repopulate
        self.tree.delete(*self.tree.get_children())
        for i, item in enumerate(items, 1):
            type_str = item.get('category', item['type']).capitalize()
            self.tree.insert('', 'end', text=str(i), values=(
                item['name'],
                type_str,
                self.analyzer.format_bytes(item['size']),
                item['path']
            ))
    
    def cancel_scan(self):
        """Cancel ongoing scan"""
        self.analyzer.cancel_flag = True
        self.progress_var.set("Cancelling...")
    
    def scan_complete(self):
        """Handle scan completion"""
        self.scanning = False
        self.scan_btn.config(state='normal')
        self.cancel_btn.config(state='disabled')
        self.progress_bar.stop()
        
        if self.analyzer.cancel_flag:
            self.progress_var.set("Scan cancelled")
            self.status_var.set("Scan cancelled by user")
            return
        
        self.progress_var.set("Scan complete!")
        self.update_display()
        
    def scan_error(self, error_msg):
        """Handle scan error"""
        self.scanning = False
        self.scan_btn.config(state='normal')
        self.cancel_btn.config(state='disabled')
        self.progress_bar.stop()
        messagebox.showerror("Scan Error", f"Error during scan:\n{error_msg}")
        self.progress_var.set("Scan failed")
    
    def update_display(self):
        """Update UI with scan results"""
        if not self.current_results:
            return
        
        # Update stats
        self.stats_labels['total_size'].config(
            text=self.analyzer.format_bytes(self.current_results['total_size']))
        self.stats_labels['files'].config(
            text=f"{self.current_results['file_count']:,}")
        self.stats_labels['folders'].config(
            text=f"{self.current_results['dir_count']:,}")
        
        if self.current_results['all_items']:
            largest = max(self.current_results['all_items'], key=lambda x: x['size'])
            self.stats_labels['largest'].config(
                text=self.analyzer.format_bytes(largest['size']))
        
        # Update categories and pie chart
        self.draw_categories(self.current_results)
        self.draw_pie_chart(self.current_results)
        
        # Update table
        self.apply_filter()
        
        self.status_var.set(f"Found {self.current_results['file_count']:,} files in {self.current_results['dir_count']:,} folders")
    
    def draw_categories(self, results=None):
        """Draw category breakdown chart"""
        self.category_canvas.delete("all")
        
        if not results:
            results = self.current_results
        
        if not results or results['total_size'] == 0:
            return
        
        categories = results['categories']
        total = results['total_size']
        
        colors = {
            'video': '#E91E63',
            'image': '#2196F3',
            'pdf': '#f44336',
            'document': '#4CAF50',
            'archive': '#FF9800',
            'audio': '#9C27B0',
            'code': '#00BCD4',
            'other': '#757575'
        }
        
        width = self.category_canvas.winfo_width()
        if width <= 1:
            width = 600
        
        y_offset = 10
        bar_height = 20
        
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        
        for category, size in sorted_cats:
            if size == 0:
                continue
            percentage = (size / total) * 100
            bar_width = (size / total) * (width - 250)
            
            # Draw bar
            color = colors.get(category, '#757575')
            self.category_canvas.create_rectangle(
                100, y_offset, 100 + bar_width, y_offset + bar_height,
                fill=color, outline=color
            )
            
            # Draw label
            self.category_canvas.create_text(
                5, y_offset + bar_height/2,
                text=category.capitalize(),
                anchor=tk.W,
                font=('Arial', 9, 'bold')
            )
            
            # Draw size and percentage
            size_text = f"{self.analyzer.format_bytes(size)} ({percentage:.1f}%)"
            self.category_canvas.create_text(
                110 + bar_width, y_offset + bar_height/2,
                text=size_text,
                anchor=tk.W,
                font=('Arial', 9)
            )
            
            y_offset += bar_height + 5
    
    def draw_pie_chart(self, results=None):
        """Draw pie chart visualization (camembert)"""
        import math
        
        self.pie_canvas.delete("all")
        
        if not results:
            results = self.current_results
        
        if not results or results['total_size'] == 0:
            return
        
        categories = results['categories']
        total = results['total_size']
        
        if total == 0:
            return
        
        colors = {
            'video': '#E91E63',
            'image': '#2196F3',
            'pdf': '#f44336',
            'document': '#4CAF50',
            'archive': '#FF9800',
            'audio': '#9C27B0',
            'code': '#00BCD4',
            'other': '#757575'
        }
        
        # Pie chart settings
        center_x = 125
        center_y = 125
        radius = 80
        
        # Draw pie slices
        start_angle = 0
        sorted_cats = sorted(categories.items(), key=lambda x: x[1], reverse=True)
        
        for category, size in sorted_cats:
            if size == 0:
                continue
                
            percentage = size / total
            extent = percentage * 360
            
            color = colors.get(category, '#757575')
            
            # Draw slice
            self.pie_canvas.create_arc(
                center_x - radius, center_y - radius,
                center_x + radius, center_y + radius,
                start=start_angle, extent=extent,
                fill=color, outline='white', width=2
            )
            
            start_angle += extent
        
        # Draw legend below pie
        legend_y = 220
        legend_x = 10
        
        for i, (category, size) in enumerate(sorted_cats[:8]):  # Top 8 categories
            if size == 0:
                continue
                
            color = colors.get(category, '#757575')
            percentage = (size / total) * 100
            
            # Draw color box
            if i < 4:
                x = legend_x
                y = legend_y + (i * 20)
            else:
                x = legend_x + 125
                y = legend_y + ((i - 4) * 20)
            
            self.pie_canvas.create_rectangle(
                x, y, x + 12, y + 12,
                fill=color, outline=color
            )
            
            # Draw label
            label = f"{category[:3].upper()} {percentage:.0f}%"
            self.pie_canvas.create_text(
                x + 16, y + 6,
                text=label,
                anchor=tk.W,
                font=('Arial', 8)
            )
    
    def apply_filter(self):
        """Apply current filter and sort settings"""
        if not self.current_results:
            return
        
        self.tree.delete(*self.tree.get_children())
        
        # Filter items
        items = self.current_results['all_items']
        filter_type = self.filter_var.get()
        
        if filter_type == 'files':
            items = [x for x in items if x['type'] == 'file']
        elif filter_type == 'folders':
            items = [x for x in items if x['type'] == 'folder']
        
        # Sort items
        if self.sort_var.get() == 'name':
            items = sorted(items, key=lambda x: x['name'].lower())
        else:
            items = sorted(items, key=lambda x: x['size'], reverse=True)
        
        # Populate tree (limit to 1000 for performance)
        for i, item in enumerate(items[:1000], 1):
            type_str = item.get('category', item['type']).capitalize()
            self.tree.insert('', 'end', text=str(i), values=(
                item['name'],
                type_str,
                self.analyzer.format_bytes(item['size']),
                item['path']
            ))
        
        if len(items) > 1000:
            self.status_var.set(f"Showing top 1000 of {len(items):,} items")
        else:
            self.status_var.set(f"Showing {len(items):,} items")
    
    def show_context_menu(self, event):
        """Show context menu on right-click"""
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
    
    def delete_selected(self):
        """Move selected item to trash"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        path = item['values'][3]
        
        if messagebox.askyesno("Confirm", f"Move to trash?\n\n{path}"):
            try:
                trash_dir = Path.home() / '.local' / 'share' / 'Trash' / 'files'
                trash_dir.mkdir(parents=True, exist_ok=True)
                
                source = Path(path)
                dest = trash_dir / source.name
                
                # Handle name collision
                counter = 1
                while dest.exists():
                    dest = trash_dir / f"{source.stem}_{counter}{source.suffix}"
                    counter += 1
                
                import shutil
                shutil.move(str(source), str(dest))
                
                messagebox.showinfo("Success", "Item moved to trash")
                self.start_scan()  # Rescan
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to move to trash:\n{e}")
    
    def open_in_filemanager(self):
        """Open selected item in file manager"""
        selection = self.tree.selection()
        if not selection:
            return
        
        item = self.tree.item(selection[0])
        path = item['values'][3]
        
        try:
            subprocess.run(['xdg-open', str(Path(path).parent)], check=False)
        except:
            messagebox.showerror("Error", "Could not open file manager")


def main():
    """Main entry point"""
    if not HAVE_GUI:
        print("\n" + "="*60)
        print("ERROR: GUI libraries not available")
        print("="*60)
        print("\nPlease install Tkinter:")
        print("  sudo apt-get update")
        print("  sudo apt-get install python3-tk")
        print("\nThen run this application again.")
        print("="*60)
        sys.exit(1)
    
    root = tk.Tk()
    app = DiskAnalyzerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
