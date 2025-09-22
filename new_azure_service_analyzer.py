#!/usr/bin/env python3
"""
Azure Service Usage Analyzer
Analyzes Azure usage CSV data and organizes it by service categories,
subcategories, and their unit/total relationships.
Can compare two CSV files side by side.
"""

import pandas as pd
import sys
from collections import defaultdict
import os
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import tempfile

def analyze_azure_services(csv_file_path):
    """
    Analyze Azure service usage from CSV file.

    Args:
        csv_file_path (str): Path to the CSV file

    Returns:
        dict: Organized service data
    """
    try:
        # Read the CSV file
        print(f"Loading CSV file: {csv_file_path}")
        df = pd.read_csv(csv_file_path)
        print(f"Successfully loaded {len(df)} rows of data\n")

        # Check if required columns exist
        required_columns = ['service_category', 'service_sub_category', 'service_unit', 'total']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            print(f"Error: Missing required columns: {missing_columns}")
            return None

        # Remove rows with missing service category data
        df_clean = df.dropna(subset=['service_category'])
        print(f"Analyzing {len(df_clean)} rows after removing incomplete data")

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

        return dict(service_data)

    except FileNotFoundError:
        print(f"Error: File '{csv_file_path}' not found.")
        return None
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        return None

def calculate_category_totals(service_data):
    """
    Calculate category totals for service data.

    Args:
        service_data (dict): Organized service data

    Returns:
        dict: Category totals
    """
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

def generate_single_analysis_pdf(service_data, file_name, output_path=None):
    """
    Generate PDF report for single file analysis.

    Args:
        service_data (dict): Organized service data
        file_name (str): Name of the analyzed file
        output_path (str): Path for the output PDF file

    Returns:
        str: Path to generated PDF file
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"azure_analysis_{timestamp}.pdf"

    # Create PDF document
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.blue,
        alignment=1,  # Center alignment
        spaceAfter=30
    )

    story.append(Paragraph("📊 Azure Service Usage Analysis", title_style))
    story.append(Paragraph(f"File: {os.path.basename(file_name)}", styles['Heading2']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 20))

    # Summary statistics
    sorted_categories = sorted(service_data.keys())
    category_totals = calculate_category_totals(service_data)

    total_subcategories = sum(len(subcats) for subcats in service_data.values())
    total_unit_types = sum(
        len(units) for subcats in service_data.values()
        for units in subcats.values()
    )
    grand_total = sum(category_totals.values())

    # Summary table
    summary_data = [
        ['📈 Summary Statistics', ''],
        ['Total Service Categories:', str(len(sorted_categories))],
        ['Total Service Subcategories:', str(total_subcategories)],
        ['Total Unit Types:', str(total_unit_types)],
        ['Grand Total Amount:', f'{grand_total:,.2f}']
    ]

    summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(summary_table)
    story.append(Spacer(1, 20))

    # Top 5 categories
    story.append(Paragraph("🏆 Top 5 Categories by Total Amount", styles['Heading3']))
    sorted_by_total = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]

    top_categories_data = [['Rank', 'Category', 'Total Amount']]
    for i, (category, total) in enumerate(sorted_by_total, 1):
        top_categories_data.append([str(i), category, f'{total:,.2f}'])

    top_table = Table(top_categories_data, colWidths=[0.5*inch, 3*inch, 1.5*inch])
    top_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(top_table)
    story.append(PageBreak())

    # Detailed breakdown
    story.append(Paragraph("📋 Detailed Service Breakdown", styles['Heading2']))
    story.append(Spacer(1, 10))

    for category in sorted_categories:
        story.append(Paragraph(f"🔵 {category}", styles['Heading3']))

        subcategories = service_data[category]
        sorted_subcategories = sorted(subcategories.keys())

        for subcategory in sorted_subcategories:
            story.append(Paragraph(f"📂 {subcategory}", styles['Heading4']))

            units = subcategories[subcategory]
            sorted_units = sorted(units.keys())

            unit_data = [['Unit', 'Total Amount']]
            subcategory_total = 0

            for unit in sorted_units:
                total_amount = units[unit]
                subcategory_total += total_amount
                unit_data.append([unit, f'{total_amount:,.2f}'])

            unit_data.append(['📊 Subcategory Total', f'{subcategory_total:,.2f}'])

            unit_table = Table(unit_data, colWidths=[3*inch, 2*inch])
            unit_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, -1), (-1, -1), colors.yellow),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))

            story.append(unit_table)
            story.append(Spacer(1, 5))

        category_total = category_totals[category]
        story.append(Paragraph(f"✅ Category Total: {category_total:,.2f}", styles['Heading4']))
        story.append(Spacer(1, 15))

    # Build PDF
    doc.build(story)
    print(f"✅ PDF report generated: {output_path}")
    return output_path

def generate_comparison_pdf(old_data, new_data, old_file_name, new_file_name, output_path=None):
    """
    Generate PDF report for dual file comparison.

    Args:
        old_data (dict): First dataset (old)
        new_data (dict): Second dataset (new)
        old_file_name (str): Name of first file
        new_file_name (str): Name of second file
        output_path (str): Path for the output PDF file

    Returns:
        str: Path to generated PDF file
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"azure_comparison_{timestamp}.pdf"

    # Create PDF document
    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.blue,
        alignment=1,
        spaceAfter=30
    )

    story.append(Paragraph("📊 Azure Service Usage Comparison", title_style))
    story.append(Paragraph(f"Old File: {old_file_name}", styles['Heading3']))
    story.append(Paragraph(f"New File: {new_file_name}", styles['Heading3']))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
    story.append(Spacer(1, 20))

    # Calculate totals
    old_totals = calculate_category_totals(old_data) if old_data else {}
    new_totals = calculate_category_totals(new_data) if new_data else {}

    # Summary comparison
    old_categories_count = len(old_data) if old_data else 0
    new_categories_count = len(new_data) if new_data else 0
    old_subcats = sum(len(subcats) for subcats in old_data.values()) if old_data else 0
    new_subcats = sum(len(subcats) for subcats in new_data.values()) if new_data else 0
    old_grand_total = sum(old_totals.values())
    new_grand_total = sum(new_totals.values())

    comparison_data = [
        ['📈 Comparison Summary', 'Old File', 'New File'],
        ['Service Categories:', str(old_categories_count), str(new_categories_count)],
        ['Service Subcategories:', str(old_subcats), str(new_subcats)],
        ['Grand Total Amount:', f'{old_grand_total:,.2f}', f'{new_grand_total:,.2f}']
    ]

    comparison_table = Table(comparison_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch])
    comparison_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))

    story.append(comparison_table)
    story.append(Spacer(1, 20))

    # Service changes
    missing_services, added_services = compare_service_data(old_data, new_data)

    if missing_services or added_services:
        story.append(Paragraph("🔄 Service Changes", styles['Heading3']))

        if missing_services:
            story.append(Paragraph(f"❌ Services Missing from New File ({len(missing_services)}):", styles['Heading4']))
            for service in missing_services:
                story.append(Paragraph(f"• {service}", styles['Normal']))
            story.append(Spacer(1, 10))

        if added_services:
            story.append(Paragraph(f"⭐ New Services Added ({len(added_services)}):", styles['Heading4']))
            for service in added_services:
                story.append(Paragraph(f"• {service}", styles['Normal']))
            story.append(Spacer(1, 10))
    else:
        story.append(Paragraph("🔄 No service changes detected", styles['Heading3']))

    story.append(PageBreak())

    # Detailed Comparison
    story.append(Paragraph("📋 Detailed Service Comparison", styles['Heading2']))
    story.append(Spacer(1, 10))

    all_categories = sorted(list(set(old_data.keys()) | set(new_data.keys())))

    for category in all_categories:
        story.append(Paragraph(f"🔵 {category}", styles['Heading3']))

        old_cat_data = old_data.get(category, {})
        new_cat_data = new_data.get(category, {})

        all_subcategories = sorted(list(set(old_cat_data.keys()) | set(new_cat_data.keys())))

        for subcategory in all_subcategories:
            story.append(Paragraph(f"📂 {subcategory}", styles['Heading4']))

            old_sub_data = old_cat_data.get(subcategory, {})
            new_sub_data = new_cat_data.get(subcategory, {})

            all_units = sorted(list(set(old_sub_data.keys()) | set(new_sub_data.keys())))

            table_data = [['Unit', 'Old Amount', 'New Amount', 'Change']]

            for unit in all_units:
                old_amount = old_sub_data.get(unit, 0)
                new_amount = new_sub_data.get(unit, 0)
                change = new_amount - old_amount

                # Format the change with a sign
                change_str = f"{change:,.2f}"
                if change > 0:
                    change_str = f"+{change_str}"

                table_data.append([
                    unit,
                    f"{old_amount:,.2f}",
                    f"{new_amount:,.2f}",
                    change_str
                ])

            comp_table = Table(table_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1*inch])
            comp_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                # Color code the change column
                ('TEXTCOLOR', (3, 1), (3, -1), colors.black),
            ]))

            # Add conditional coloring for the change column
            for i, row in enumerate(table_data[1:], 1):
                change_val_str = row[3].replace('+', '').replace(',', '')
                try:
                    change_val = float(change_val_str)
                    if change_val > 0:
                        comp_table.setStyle(TableStyle([('TEXTCOLOR', (3, i), (3, i), colors.red)]))
                    elif change_val < 0:
                        comp_table.setStyle(TableStyle([('TEXTCOLOR', (3, i), (3, i), colors.green)]))
                except ValueError:
                    pass # Should not happen, but good to be safe

            story.append(comp_table)
            story.append(Spacer(1, 5))

        story.append(Spacer(1, 15))

    # Build PDF
    doc.build(story)
    print(f"✅ PDF comparison report generated: {output_path}")
    return output_path

def compare_service_data(old_data, new_data):
    """
    Compare two service datasets to find added and removed services.

    Args:
        old_data (dict): First dataset (old)
        new_data (dict): Second dataset (new)

    Returns:
        tuple: (missing_services, added_services)
    """
    old_categories = set(old_data.keys()) if old_data else set()
    new_categories = set(new_data.keys()) if new_data else set()

    missing_services = old_categories - new_categories
    added_services = new_categories - old_categories

    return sorted(missing_services), sorted(added_services)

def display_dual_service_comparison(old_data, new_data, old_file_name, new_file_name):
    """
    Display two service datasets side by side for comparison.

    Args:
        old_data (dict): First dataset (old)
        new_data (dict): Second dataset (new)
        old_file_name (str): Name of first file
        new_file_name (str): Name of second file
    """
    print("=" * 160)
    print("AZURE SERVICE USAGE COMPARISON")
    print("=" * 160)

    # Headers
    left_header = f"OLD FILE: {old_file_name}"
    right_header = f"NEW FILE: {new_file_name}"
    print(f"{left_header:<80} | {right_header}")
    print("-" * 80 + " | " + "-" * 80)

    # Get all unique categories from both datasets
    all_categories = set()
    if old_data:
        all_categories.update(old_data.keys())
    if new_data:
        all_categories.update(new_data.keys())

    sorted_categories = sorted(all_categories)

    # Calculate totals for both datasets
    old_totals = calculate_category_totals(old_data) if old_data else {}
    new_totals = calculate_category_totals(new_data) if new_data else {}

    for category in sorted_categories:
        # Left side (old data)
        left_content = []
        if category in old_data:
            left_content.append(f"🔵 {category}")
            subcategories = old_data[category]
            sorted_subcategories = sorted(subcategories.keys())

            for subcategory in sorted_subcategories:
                left_content.append(f"  📂 {subcategory}")
                units = subcategories[subcategory]
                sorted_units = sorted(units.keys())

                for unit in sorted_units:
                    total_amount = units[unit]
                    left_content.append(f"    📊 {unit}: {total_amount:,.2f}")

            old_total = old_totals.get(category, 0)
            left_content.append(f"  ✅ TOTAL: {old_total:,.2f}")
        else:
            left_content.append(f"❌ {category} (MISSING)")

        # Right side (new data)
        right_content = []
        if category in new_data:
            # Check if this category is new (not in old data)
            if category not in old_data:
                right_content.append(f"🔵 {category} ⭐ (NEW)")
            else:
                right_content.append(f"🔵 {category}")

            subcategories = new_data[category]
            sorted_subcategories = sorted(subcategories.keys())

            for subcategory in sorted_subcategories:
                right_content.append(f"  📂 {subcategory}")
                units = subcategories[subcategory]
                sorted_units = sorted(units.keys())

                for unit in sorted_units:
                    total_amount = units[unit]
                    right_content.append(f"    📊 {unit}: {total_amount:,.2f}")

            new_total = new_totals.get(category, 0)
            right_content.append(f"  ✅ TOTAL: {new_total:,.2f}")
        else:
            right_content.append(f"❌ {category} (MISSING)")

        # Display side by side
        max_lines = max(len(left_content), len(right_content))
        for i in range(max_lines):
            left_line = left_content[i] if i < len(left_content) else ""
            right_line = right_content[i] if i < len(right_content) else ""
            print(f"{left_line:<80} | {right_line}")

        print("-" * 80 + " | " + "-" * 80)

    # Summary comparison
    print("\n" + "=" * 160)
    print("COMPARISON SUMMARY")
    print("=" * 160)

    # File summaries side by side
    old_categories_count = len(old_data) if old_data else 0
    new_categories_count = len(new_data) if new_data else 0

    old_subcats = sum(len(subcats) for subcats in old_data.values()) if old_data else 0
    new_subcats = sum(len(subcats) for subcats in new_data.values()) if new_data else 0

    old_units = sum(len(units) for subcats in old_data.values() for units in subcats.values()) if old_data else 0
    new_units = sum(len(units) for subcats in new_data.values() for units in subcats.values()) if new_data else 0

    old_grand_total = sum(old_totals.values())
    new_grand_total = sum(new_totals.values())

    print(f"{'OLD FILE SUMMARY':<80} | {'NEW FILE SUMMARY'}")
    print(f"{'Service Categories: ' + str(old_categories_count):<80} | {'Service Categories: ' + str(new_categories_count)}")
    print(f"{'Service Subcategories: ' + str(old_subcats):<80} | {'Service Subcategories: ' + str(new_subcats)}")
    print(f"{'Unit Types: ' + str(old_units):<80} | {'Unit Types: ' + str(new_units)}")
    print(f"{'Grand Total Amount: ' + f'{old_grand_total:,.2f}':<80} | {'Grand Total Amount: ' + f'{new_grand_total:,.2f}'}")

    # Service changes
    missing_services, added_services = compare_service_data(old_data, new_data)

    print("\n" + "=" * 80)
    print("SERVICE CHANGES")
    print("=" * 80)

    if missing_services:
        print(f"❌ SERVICES MISSING FROM NEW FILE ({len(missing_services)}):")
        for service in missing_services:
            print(f"  - {service}")
    else:
        print("❌ No services missing from new file")

    if added_services:
        print(f"\n⭐ NEW SERVICES ADDED ({len(added_services)}):")
        for service in added_services:
            print(f"  + {service}")
    else:
        print("\n⭐ No new services added")

    # Top categories comparison
    print("\n" + "=" * 80)
    print("TOP CATEGORIES COMPARISON")
    print("=" * 80)

    print(f"{'OLD FILE - TOP 5':<40} | {'NEW FILE - TOP 5'}")
    print("-" * 40 + " | " + "-" * 40)

    old_sorted = sorted(old_totals.items(), key=lambda x: x[1], reverse=True)[:5] if old_totals else []
    new_sorted = sorted(new_totals.items(), key=lambda x: x[1], reverse=True)[:5] if new_totals else []

    max_rows = max(len(old_sorted), len(new_sorted))
    for i in range(max_rows):
        if i < len(old_sorted):
            old_cat, old_val = old_sorted[i]
            old_line = f"{i+1}. {old_cat}: {old_val:,.2f}"
        else:
            old_line = ""

        if i < len(new_sorted):
            new_cat, new_val = new_sorted[i]
            new_line = f"{i+1}. {new_cat}: {new_val:,.2f}"
        else:
            new_line = ""

        print(f"{old_line:<40} | {new_line}")

def display_service_analysis(service_data):
    """
    Display the analyzed service data in an organized format.

    Args:
        service_data (dict): Organized service data
    """
    if not service_data:
        print("No data to display.")
        return

    print("=" * 80)
    print("AZURE SERVICE USAGE ANALYSIS")
    print("=" * 80)

    # Sort service categories alphabetically
    sorted_categories = sorted(service_data.keys())

    category_totals = {}

    for category in sorted_categories:
        print(f"\n🔵 SERVICE CATEGORY: {category}")
        print("-" * 60)

        category_total = 0
        subcategories = service_data[category]
        sorted_subcategories = sorted(subcategories.keys())

        for subcategory in sorted_subcategories:
            print(f"  📂 Subcategory: {subcategory}")

            units = subcategories[subcategory]
            sorted_units = sorted(units.keys())

            subcategory_total = 0

            for unit in sorted_units:
                total_amount = units[unit]
                subcategory_total += total_amount
                print(f"    📊 Unit: {unit} | Total Amount: {total_amount:,.2f}")

            print(f"    ➤ Subcategory Total: {subcategory_total:,.2f}")
            print()
            category_total += subcategory_total

        category_totals[category] = category_total
        print(f"  ✅ CATEGORY TOTAL: {category_total:,.2f}")
        print()

    # Summary section
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    print(f"Total Service Categories: {len(sorted_categories)}")

    total_subcategories = sum(len(subcats) for subcats in service_data.values())
    print(f"Total Service Subcategories: {total_subcategories}")

    total_unit_types = sum(
        len(units) for subcats in service_data.values()
        for units in subcats.values()
    )
    print(f"Total Unit Types: {total_unit_types}")

    grand_total = sum(category_totals.values())
    print(f"Grand Total Amount: {grand_total:,.2f}")

    print("\nTop Categories by Total Amount:")
    sorted_by_total = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)
    for i, (category, total) in enumerate(sorted_by_total[:5], 1):
        print(f"  {i}. {category}: {total:,.2f}")

def main():
    """
    Main function to run the Azure service analyzer.
    Supports single file analysis or dual file comparison.
    """
    # Default CSV file path
    default_csv_path = "attached_assets/az_usage_history_09_15_2025_6c16248dcada4756972a9859fedab0db_1758134557815.csv"

    print("Azure Service Usage Analyzer")
    print("=" * 40)

    # Handle command line arguments
    if len(sys.argv) == 3:
        # Dual file comparison mode
        old_csv_path = sys.argv[1]
        new_csv_path = sys.argv[2]

        # Check if both files exist
        if not os.path.exists(old_csv_path):
            print(f"Error: Old CSV file '{old_csv_path}' not found.")
            return
        if not os.path.exists(new_csv_path):
            print(f"Error: New CSV file '{new_csv_path}' not found.")
            return

        print("DUAL FILE COMPARISON MODE")
        print(f"Comparing: {old_csv_path} vs {new_csv_path}")
        print("=" * 40)

        # Analyze both files
        old_service_data = analyze_azure_services(old_csv_path)
        new_service_data = analyze_azure_services(new_csv_path)

        if old_service_data is not None and new_service_data is not None:
            # Display dual comparison
            old_file_name = os.path.basename(old_csv_path)
            new_file_name = os.path.basename(new_csv_path)
            display_dual_service_comparison(old_service_data, new_service_data, old_file_name, new_file_name)

            print("\n" + "=" * 160)
            print("COMPARISON COMPLETE!")
            print("=" * 160)
        else:
            print("Failed to analyze one or both CSV files. Please check the file formats and try again.")

    elif len(sys.argv) == 2:
        # Single file analysis mode
        csv_file_path = sys.argv[1]

        if not os.path.exists(csv_file_path):
            print(f"Error: CSV file '{csv_file_path}' not found.")
            return

        print("SINGLE FILE ANALYSIS MODE")
        print("=" * 40)

        # Analyze the service data
        service_data = analyze_azure_services(csv_file_path)

        if service_data:
            # Display the analysis
            display_service_analysis(service_data)

            print("\n" + "=" * 80)
            print("Analysis Complete!")
            print("=" * 80)
        else:
            print("Failed to analyze the CSV file. Please check the file format and try again.")

    else:
        # Default single file mode with built-in file
        if os.path.exists(default_csv_path):
            print("DEFAULT FILE ANALYSIS MODE")
            print("=" * 40)

            service_data = analyze_azure_services(default_csv_path)

            if service_data:
                display_service_analysis(service_data)
                print("\n" + "=" * 80)
                print("Analysis Complete!")
                print("=" * 80)
            else:
                print("Failed to analyze the default CSV file.")
        else:
            print("Usage options:")
            print(f"  Single file: python {sys.argv[0]} <csv_file_path>")
            print(f"  Compare files: python {sys.argv[0]} <old_file_path> <new_file_path>")
            print(f"  Example: python {sys.argv[0]} old_usage.csv new_usage.csv")

if __name__ == "__main__":
    main()
