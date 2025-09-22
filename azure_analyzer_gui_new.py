#!/usr/bin/env python3
"""
Azure Service Usage Analyzer - GUI Version
Graphical interface for analyzing Azure usage CSV data with file selection menu.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, Menu
import pandas as pd
from collections import defaultdict
import os
import threading
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import tempfile

# Import PDF functions from the CLI version
from new_azure_service_analyzer import generate_single_analysis_pdf, generate_comparison_pdf

class AzureAnalyzerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Azure Service Usage Analyzer")
        self.root.geometry("1200x800")

        # Variables to store file paths
        self.old_file_path = tk.StringVar()
        self.new_file_path = tk.StringVar()

        # To store the last analysis results for PDF generation
        self.last_analysis_type = None
        self.last_single_data = None
        self.last_comparison_data = None

        # Initialize GUI components
        self.create_menu()
        self.create_widgets()

    def create_menu(self):
        """Create the menu bar."""
        menubar = Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Select First File", command=self.select_old_file)
        file_menu.add_command(label="Select Second File", command=self.select_new_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        # Analysis menu
        analysis_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Analysis", menu=analysis_menu)
        analysis_menu.add_command(label="Analyze Single File", command=self.analyze_single)
        analysis_menu.add_command(label="Compare Two Files", command=self.analyze_comparison)
        analysis_menu.add_command(label="Clear Results", command=self.clear_results)

        # Help menu
        help_menu = Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)

    def create_widgets(self):
        """Create the main GUI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="wens")

        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="File Selection", padding="10")
        file_frame.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 10))
        file_frame.columnconfigure(1, weight=1)

        # First file selection
        ttk.Label(file_frame, text="First File (Old):").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.old_file_path, width=80).grid(row=0, column=1, sticky="we", padx=(5, 0), pady=2)
        ttk.Button(file_frame, text="Browse", command=self.select_old_file).grid(row=0, column=2, padx=(5, 0), pady=2)

        # Second file selection
        ttk.Label(file_frame, text="Second File (New):").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(file_frame, textvariable=self.new_file_path, width=80).grid(row=1, column=1, sticky="we", padx=(5, 0), pady=2)
        ttk.Button(file_frame, text="Browse", command=self.select_new_file).grid(row=1, column=2, padx=(5, 0), pady=2)

        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)

        ttk.Button(button_frame, text="Analyze Single File", command=self.analyze_single).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Compare Two Files", command=self.analyze_comparison).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear Results", command=self.clear_results).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Convert to PDF", command=self.generate_pdf).pack(side=tk.LEFT, padx=5)

        # Results display
        results_frame = ttk.LabelFrame(main_frame, text="Analysis Results", padding="5")
        results_frame.grid(row=2, column=0, columnspan=2, sticky="wens", pady=(10, 0))
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(0, weight=1)

        # Scrollable text widget for results
        self.results_text = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, font=('Courier', 10))
        self.results_text.grid(row=0, column=0, sticky="wens")

        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.grid(row=3, column=0, columnspan=2, sticky="we", pady=(5, 0))

    def select_old_file(self):
        """Open file dialog to select the first CSV file."""
        filename = filedialog.askopenfilename(
            title="Select First CSV File (Old)",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.old_file_path.set(filename)

    def select_new_file(self):
        """Open file dialog to select the second CSV file."""
        filename = filedialog.askopenfilename(
            title="Select Second CSV File (New)",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.new_file_path.set(filename)

    def clear_results(self):
        """Clear the results display."""
        self.results_text.delete(1.0, tk.END)
        self.last_analysis_type = None
        self.last_single_data = None
        self.last_comparison_data = None

    def show_progress(self):
        """Show progress bar."""
        self.progress.start()

    def hide_progress(self):
        """Hide progress bar."""
        self.progress.stop()

    def analyze_single(self):
        """Analyze a single file."""
        if not self.old_file_path.get():
            messagebox.showerror("Error", "Please select a CSV file to analyze.")
            return

        # Run analysis in separate thread to prevent GUI freezing
        def run_analysis():
            try:
                # Start progress on main thread
                self.root.after(0, self.show_progress)
                self.root.after(0, self.clear_results)
                self.root.after(0, lambda: self.results_text.insert(tk.END, "Analyzing file...\n\n"))

                service_data, error_msg = self.analyze_azure_services(self.old_file_path.get())

                if service_data:
                    # Store results for PDF generation
                    self.last_analysis_type = "single"
                    self.last_single_data = service_data

                    result_text = self.format_single_analysis(service_data, self.old_file_path.get())
                    self.root.after(0, lambda: self.results_text.delete(1.0, tk.END))
                    self.root.after(0, lambda: self.results_text.insert(tk.END, result_text))
                else:
                    self.last_analysis_type = None
                    error_text = error_msg or "Failed to analyze the CSV file. Please check the file format."
                    self.root.after(0, lambda: self.results_text.insert(tk.END, error_text))
                    self.root.after(0, lambda: messagebox.showerror("Analysis Error", error_text))

            except Exception as e:
                self.last_analysis_type = None
                self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred during analysis: {str(e)}"))
            finally:
                self.root.after(0, self.hide_progress)

        threading.Thread(target=run_analysis, daemon=True).start()

    def analyze_comparison(self):
        """Compare two files."""
        if not self.old_file_path.get() or not self.new_file_path.get():
            messagebox.showerror("Error", "Please select both CSV files for comparison.")
            return

        # Run analysis in separate thread to prevent GUI freezing
        def run_comparison():
            try:
                # Start progress on main thread
                self.root.after(0, self.show_progress)
                self.root.after(0, self.clear_results)
                self.root.after(0, lambda: self.results_text.insert(tk.END, "Comparing files...\n\n"))

                old_data, old_error = self.analyze_azure_services(self.old_file_path.get())
                new_data, new_error = self.analyze_azure_services(self.new_file_path.get())

                if old_data is not None and new_data is not None:
                    # Store results for PDF generation
                    self.last_analysis_type = "comparison"
                    self.last_comparison_data = (old_data, new_data)

                    result_text = self.format_comparison_analysis(old_data, new_data,
                                                               self.old_file_path.get(),
                                                               self.new_file_path.get())
                    self.root.after(0, lambda: self.results_text.delete(1.0, tk.END))
                    self.root.after(0, lambda: self.results_text.insert(tk.END, result_text))
                else:
                    self.last_analysis_type = None
                    error_text = "Analysis errors:\n"
                    if old_error:
                        error_text += f"Old file: {old_error}\n"
                    if new_error:
                        error_text += f"New file: {new_error}\n"
                    if not old_error and not new_error:
                        error_text = "Failed to analyze one or both CSV files. Please check the file formats."
                    self.root.after(0, lambda: self.results_text.insert(tk.END, error_text))
                    self.root.after(0, lambda: messagebox.showerror("Comparison Error", error_text))

            except Exception as e:
                self.last_analysis_type = None
                self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred during comparison: {str(e)}"))
            finally:
                self.root.after(0, self.hide_progress)

        threading.Thread(target=run_comparison, daemon=True).start()

    def generate_pdf(self):
        """Generate PDF report for the last analysis."""
        if not self.last_analysis_type:
            messagebox.showerror("Error", "Please run an analysis first.")
            return

        output_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
            title="Save PDF Report"
        )

        if not output_path:
            return

        try:
            self.show_progress()
            if self.last_analysis_type == "single":
                generate_single_analysis_pdf(self.last_single_data, self.old_file_path.get(), output_path)
            elif self.last_analysis_type == "comparison":
                old_data, new_data = self.last_comparison_data
                generate_comparison_pdf(old_data, new_data, self.old_file_path.get(), self.new_file_path.get(), output_path)

            messagebox.showinfo("Success", f"PDF report saved to:\n{output_path}")

        except Exception as e:
            messagebox.showerror("PDF Generation Error", f"An error occurred while generating the PDF: {str(e)}")
        finally:
            self.hide_progress()

    def analyze_azure_services(self, csv_file_path):
        """
        Analyze Azure service usage from CSV file.

        Args:
            csv_file_path (str): Path to the CSV file

        Returns:
            tuple: (dict: Organized service data, str: Error message if any)
        """
        try:
            # Read the CSV file
            df = pd.read_csv(csv_file_path)

            # Check if required columns exist
            required_columns = ['service_category', 'service_sub_category', 'service_unit', 'total']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                return None, f"Missing required columns: {missing_columns}"

            # Remove rows with missing service category data
            df_clean = df.dropna(subset=['service_category'])

            # Convert total to numeric, handling any non-numeric values
            df_clean['total'] = pd.to_numeric(df_clean['total'], errors='coerce')
            df_clean = df_clean.dropna(subset=['total'])

            # Create organized data structure
            service_data = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))

            # Process each row
            for _, row in df_clean.iterrows():
                category = row['service_category']

                # Handle subcategory
                try:
                    subcategory = str(row['service_sub_category']).strip() if str(row['service_sub_category']) != 'nan' and str(row['service_sub_category']).strip() else 'N/A'
                except:
                    subcategory = 'N/A'

                # Handle unit
                try:
                    unit = str(row['service_unit']).strip() if str(row['service_unit']) != 'nan' and str(row['service_unit']).strip() else 'N/A'
                except:
                    unit = 'N/A'

                total = row['total']

                # Aggregate totals by category -> subcategory -> unit
                service_data[category][subcategory][unit] += total

            return dict(service_data), None

        except FileNotFoundError:
            return None, f"File '{csv_file_path}' not found."
        except Exception as e:
            return None, f"Error processing file: {str(e)}"

    def calculate_category_totals(self, service_data):
        """Calculate category totals for service data."""
        category_totals = {}

        for category in service_data:
            category_total = 0
            subcategories = service_data[category]

            for subcategory in subcategories:
                units = subcategories[subcategory]
                for unit in units:
                    total_amount = units[unit]
                    category_total += total_amount

            category_totals[category] = category_total

        return category_totals

    def compare_service_data(self, old_data, new_data):
        """Compare two service datasets to find added and removed services."""
        old_categories = set(old_data.keys()) if old_data else set()
        new_categories = set(new_data.keys()) if new_data else set()

        missing_services = old_categories - new_categories
        added_services = new_categories - old_categories

        return sorted(missing_services), sorted(added_services)

    def format_single_analysis(self, service_data, file_name):
        """Format single file analysis results."""
        result = []
        result.append("="*80)
        result.append("AZURE SERVICE USAGE ANALYSIS")
        result.append("="*80)
        result.append(f"File: {os.path.basename(file_name)}")
        result.append("="*80)

        # Sort service categories alphabetically
        sorted_categories = sorted(service_data.keys())

        category_totals = {}

        for category in sorted_categories:
            result.append(f"\n🔵 SERVICE CATEGORY: {category}")
            result.append("-" * 60)

            category_total = 0
            subcategories = service_data[category]
            sorted_subcategories = sorted(subcategories.keys())

            for subcategory in sorted_subcategories:
                result.append(f"  📂 Subcategory: {subcategory}")

                units = subcategories[subcategory]
                sorted_units = sorted(units.keys())

                subcategory_total = 0

                for unit in sorted_units:
                    total_amount = units[unit]
                    subcategory_total += total_amount
                    result.append(f"    📊 Unit: {unit} | Total Amount: {total_amount:,.2f}")

                result.append(f"    ➤ Subcategory Total: {subcategory_total:,.2f}")
                result.append("")
                category_total += subcategory_total

            category_totals[category] = category_total
            result.append(f"  ✅ CATEGORY TOTAL: {category_total:,.2f}")
            result.append("")

        # Summary section
        result.append("\n" + "=" * 80)
        result.append("SUMMARY")
        result.append("=" * 80)

        result.append(f"Total Service Categories: {len(sorted_categories)}")

        total_subcategories = sum(len(subcats) for subcats in service_data.values())
        result.append(f"Total Service Subcategories: {total_subcategories}")

        total_unit_types = sum(
            len(units) for subcats in service_data.values()
            for units in subcats.values()
        )
        result.append(f"Total Unit Types: {total_unit_types}")

        grand_total = sum(category_totals.values())
        result.append(f"Grand Total Amount: {grand_total:,.2f}")

        result.append("\nTop Categories by Total Amount:")
        sorted_by_total = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
        for i, (category, total) in enumerate(sorted_by_total[:5], 1):
            result.append(f"  {i}. {category}: {total:,.2f}")

        result.append("\n" + "=" * 80)
        result.append("ANALYSIS COMPLETE!")
        result.append("=" * 80)

        return "\n".join(result)

    def format_comparison_analysis(self, old_data, new_data, old_file_path, new_file_path):
        """Format comparison analysis results."""
        result = []
        result.append("="*120)
        result.append("AZURE SERVICE USAGE COMPARISON")
        result.append("="*120)

        old_file_name = os.path.basename(old_file_path)
        new_file_name = os.path.basename(new_file_path)
        result.append(f"OLD FILE: {old_file_name}")
        result.append(f"NEW FILE: {new_file_name}")
        result.append("="*120)

        # Get all unique categories from both datasets
        all_categories = set()
        if old_data:
            all_categories.update(old_data.keys())
        if new_data:
            all_categories.update(new_data.keys())

        sorted_categories = sorted(all_categories)

        # Calculate totals for both datasets
        old_totals = self.calculate_category_totals(old_data) if old_data else {}
        new_totals = self.calculate_category_totals(new_data) if new_data else {}

        for category in sorted_categories:
            result.append(f"\n🔵 SERVICE CATEGORY: {category}")
            result.append("-" * 60)

            # Show old file data
            result.append("OLD FILE:")
            if category in old_data:
                subcategories = old_data[category]
                sorted_subcategories = sorted(subcategories.keys())

                for subcategory in sorted_subcategories:
                    result.append(f"  📂 {subcategory}")
                    units = subcategories[subcategory]
                    sorted_units = sorted(units.keys())

                    for unit in sorted_units:
                        total_amount = units[unit]
                        result.append(f"    📊 {unit}: {total_amount:,.2f}")

                old_total = old_totals.get(category, 0)
                result.append(f"  ✅ TOTAL: {old_total:,.2f}")
            else:
                result.append("  ❌ MISSING")

            # Show new file data
            result.append("NEW FILE:")
            if category in new_data:
                if category not in old_data:
                    result.append(f"  ⭐ NEW SERVICE")

                subcategories = new_data[category]
                sorted_subcategories = sorted(subcategories.keys())

                for subcategory in sorted_subcategories:
                    result.append(f"  📂 {subcategory}")
                    units = subcategories[subcategory]
                    sorted_units = sorted(units.keys())

                    for unit in sorted_units:
                        total_amount = units[unit]
                        result.append(f"    📊 {unit}: {total_amount:,.2f}")

                new_total = new_totals.get(category, 0)
                result.append(f"  ✅ TOTAL: {new_total:,.2f}")
            else:
                result.append("  ❌ MISSING")

            result.append("")

        # Summary comparison
        result.append("\n" + "=" * 120)
        result.append("COMPARISON SUMMARY")
        result.append("=" * 120)

        # File summaries
        old_categories_count = len(old_data) if old_data else 0
        new_categories_count = len(new_data) if new_data else 0

        old_subcats = sum(len(subcats) for subcats in old_data.values()) if old_data else 0
        new_subcats = sum(len(subcats) for subcats in new_data.values()) if new_data else 0

        old_grand_total = sum(old_totals.values())
        new_grand_total = sum(new_totals.values())

        result.append("FILE STATISTICS:")
        result.append(f"OLD FILE - Categories: {old_categories_count}, Subcategories: {old_subcats}, Total: {old_grand_total:,.2f}")
        result.append(f"NEW FILE - Categories: {new_categories_count}, Subcategories: {new_subcats}, Total: {new_grand_total:,.2f}")

        # Service changes
        missing_services, added_services = self.compare_service_data(old_data, new_data)

        result.append("\nSERVICE CHANGES:")

        if missing_services:
            result.append(f"❌ SERVICES MISSING FROM NEW FILE ({len(missing_services)}):")
            for service in missing_services:
                result.append(f"  - {service}")
        else:
            result.append("❌ No services missing from new file")

        if added_services:
            result.append(f"\n⭐ NEW SERVICES ADDED ({len(added_services)}):")
            for service in added_services:
                result.append(f"  + {service}")
        else:
            result.append("\n⭐ No new services added")

        result.append("\n" + "=" * 120)
        result.append("COMPARISON COMPLETE!")
        result.append("=" * 120)

        return "\n".join(result)

    def show_about(self):
        """Show about dialog."""
        messagebox.showinfo("About",
                          "Azure Service Usage Analyzer v2.0\n\n"
                          "Analyzes Azure usage CSV data and compares service categories,\n"
                          "subcategories, and their unit/total relationships.\n\n"
                          "Features:\n"
                          "• Single file analysis\n"
                          "• Dual file comparison\n"
                          "• Service change detection\n"
                          "• Graphical interface with file selection")

def main():
    root = tk.Tk()
    app = AzureAnalyzerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
