"""
app/services/export_service.py - Export functionality for dashboards and reports
Supports CSV and PDF exports with background task integration for large exports.
"""

import csv
import io
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

from flask import current_app
import pandas as pd
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from app.models import ServiceRequest, ServiceRequestHistory, User

logger = logging.getLogger(__name__)


class ExportService:
    """Service for exporting dashboard data to CSV and PDF formats."""

    @staticmethod
    def export_requests_to_csv(
        requests: List[ServiceRequest],
        include_history: bool = False
    ) -> Tuple[io.StringIO, str]:
        """
        Export service requests to CSV format.
        
        Args:
            requests: List of ServiceRequest objects to export
            include_history: Whether to include request history/audit trail
            
        Returns:
            Tuple of (StringIO buffer, filename)
        """
        try:
            output = io.StringIO()
            
            if include_history:
                fieldnames = [
                    'ID', 'Title', 'Description', 'Category', 'Priority', 'Status',
                    'Created By', 'Created At', 'Assigned To', 'Due Date',
                    'Completed At', 'Resolution Time (Days)'
                ]
            else:
                fieldnames = [
                    'ID', 'Title', 'Description', 'Category', 'Priority', 'Status',
                    'Created By', 'Created At', 'Assigned To', 'Due Date'
                ]
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for req in requests:
                row = {
                    'ID': req.id,
                    'Title': req.title,
                    'Description': req.description[:100] if req.description else '',
                    'Category': req.category,
                    'Priority': req.priority,
                    'Status': req.status,
                    'Created By': req.created_by_user.full_name if req.created_by_user else 'Unknown',
                    'Created At': req.created_at.strftime('%Y-%m-%d %H:%M:%S') if req.created_at else '',
                    'Assigned To': req.assigned_to_user.full_name if req.assigned_to_user else 'Unassigned',
                    'Due Date': req.due_date.strftime('%Y-%m-%d') if req.due_date else '',
                }
                
                if include_history and req.completed_at:
                    resolution_days = (req.completed_at - req.created_at).days
                    row['Completed At'] = req.completed_at.strftime('%Y-%m-%d %H:%M:%S')
                    row['Resolution Time (Days)'] = resolution_days
                
                writer.writerow(row)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'service_requests_{timestamp}.csv'
            
            logger.info(f'Exported {len(requests)} service requests to CSV: {filename}')
            return output, filename
            
        except Exception as e:
            logger.error(f'Error exporting requests to CSV: {str(e)}')
            raise


    @staticmethod
    def export_requests_to_pdf(
        requests: List[ServiceRequest],
        title: str = 'Service Requests Report',
        include_summary: bool = True
    ) -> Tuple[io.BytesIO, str]:
        """
        Export service requests to PDF format.
        
        Args:
            requests: List of ServiceRequest objects to export
            title: Report title
            include_summary: Whether to include summary statistics
            
        Returns:
            Tuple of (BytesIO buffer, filename)
        """
        try:
            output = io.BytesIO()
            
            # Create PDF document
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            doc = SimpleDocTemplate(
                output,
                pagesize=letter,
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch,
            )
            
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f77b4'),
                spaceAfter=30,
                alignment=TA_CENTER,
            )
            story.append(Paragraph(title, title_style))
            story.append(Paragraph(f'Generated: {timestamp}', styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            
            # Summary statistics
            if include_summary:
                summary_data = [
                    ['Metric', 'Value'],
                    ['Total Requests', str(len(requests))],
                    ['Open Requests', str(sum(1 for r in requests if r.status != 'completed'))],
                    ['Completed Requests', str(sum(1 for r in requests if r.status == 'completed'))],
                    ['High Priority', str(sum(1 for r in requests if r.priority == 'high'))],
                ]
                
                summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ]))
                story.append(summary_table)
                story.append(Spacer(1, 0.3*inch))
            
            # Detailed table (show first 20 requests per page)
            page_size = 20
            for page_num, i in enumerate(range(0, len(requests), page_size)):
                if page_num > 0:
                    story.append(PageBreak())
                
                page_requests = requests[i:i+page_size]
                table_data = [['ID', 'Title', 'Category', 'Priority', 'Status', 'Assigned To']]
                
                for req in page_requests:
                    assigned = req.assigned_to_user.full_name if req.assigned_to_user else 'Unassigned'
                    table_data.append([
                        str(req.id),
                        req.title[:30],
                        req.category,
                        req.priority,
                        req.status,
                        assigned,
                    ])
                
                table = Table(table_data, colWidths=[0.6*inch, 2.5*inch, 1*inch, 0.8*inch, 0.8*inch, 1.2*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f0f0')]),
                ]))
                story.append(table)
            
            # Build PDF
            doc.build(story)
            output.seek(0)
            
            filename = f'service_requests_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            logger.info(f'Exported {len(requests)} service requests to PDF: {filename}')
            return output, filename
            
        except Exception as e:
            logger.error(f'Error exporting requests to PDF: {str(e)}')
            raise


    @staticmethod
    def export_analytics_summary_to_pdf(
        analytics_data: Dict[str, Any],
        title: str = 'Analytics Report'
    ) -> Tuple[io.BytesIO, str]:
        """
        Export analytics summary to PDF.
        
        Args:
            analytics_data: Dictionary containing analytics metrics from analytics_service
            title: Report title
            
        Returns:
            Tuple of (BytesIO buffer, filename)
        """
        try:
            output = io.BytesIO()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            doc = SimpleDocTemplate(
                output,
                pagesize=letter,
                rightMargin=0.5*inch,
                leftMargin=0.5*inch,
                topMargin=0.75*inch,
                bottomMargin=0.75*inch,
            )
            
            story = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=24,
                textColor=colors.HexColor('#1f77b4'),
                spaceAfter=30,
                alignment=TA_CENTER,
            )
            story.append(Paragraph(title, title_style))
            story.append(Paragraph(f'Generated: {timestamp}', styles['Normal']))
            story.append(Spacer(1, 0.3*inch))
            
            # Key metrics
            story.append(Paragraph('Key Metrics', styles['Heading2']))
            
            metrics_data = [
                ['Metric', 'Value'],
                ['Total Requests', str(analytics_data.get('total_requests', 0))],
                ['Unassigned Requests', str(analytics_data.get('unassigned_requests', 0))],
                ['Overdue Requests', str(analytics_data.get('overdue_requests', 0))],
                ['Average Resolution Time', f"{analytics_data.get('avg_resolution_time', 0):.1f} days"],
                ['Open Requests', str(analytics_data.get('open_requests', 0))],
                ['In Progress Requests', str(analytics_data.get('in_progress_requests', 0))],
                ['Completed Requests', str(analytics_data.get('completed_requests', 0))],
            ]
            
            metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            story.append(metrics_table)
            story.append(Spacer(1, 0.3*inch))
            
            # Status breakdown
            if analytics_data.get('status_breakdown'):
                story.append(Paragraph('Status Breakdown', styles['Heading2']))
                status_data = [['Status', 'Count']]
                for status, count in analytics_data['status_breakdown'].items():
                    status_data.append([status.title(), str(count)])
                
                status_table = Table(status_data, colWidths=[2*inch, 1*inch])
                status_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ]))
                story.append(status_table)
                story.append(Spacer(1, 0.3*inch))
            
            # Category breakdown
            if analytics_data.get('category_breakdown'):
                story.append(Paragraph('Category Breakdown', styles['Heading2']))
                category_data = [['Category', 'Count']]
                for category, count in analytics_data['category_breakdown'].items():
                    category_data.append([category.title(), str(count)])
                
                category_table = Table(category_data, colWidths=[2*inch, 1*inch])
                category_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f77b4')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ]))
                story.append(category_table)
            
            # Build PDF
            doc.build(story)
            output.seek(0)
            
            filename = f'analytics_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
            logger.info(f'Exported analytics report to PDF: {filename}')
            return output, filename
            
        except Exception as e:
            logger.error(f'Error exporting analytics to PDF: {str(e)}')
            raise


    @staticmethod
    def export_staff_performance_to_csv(
        staff_performance: List[Dict[str, Any]]
    ) -> Tuple[io.StringIO, str]:
        """
        Export staff performance metrics to CSV.
        
        Args:
            staff_performance: List of dicts with staff performance data
            
        Returns:
            Tuple of (StringIO buffer, filename)
        """
        try:
            output = io.StringIO()
            
            fieldnames = [
                'Staff Member', 'Assigned Requests', 'Completed Requests',
                'In Progress', 'Completion Rate (%)', 'Average Resolution Time (Days)'
            ]
            
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            
            for staff in staff_performance:
                writer.writerow({
                    'Staff Member': staff.get('name', 'Unknown'),
                    'Assigned Requests': staff.get('assigned_count', 0),
                    'Completed Requests': staff.get('completed_count', 0),
                    'In Progress': staff.get('in_progress_count', 0),
                    'Completion Rate (%)': f"{staff.get('completion_rate', 0):.1f}",
                    'Average Resolution Time (Days)': f"{staff.get('avg_resolution_time', 0):.1f}",
                })
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'staff_performance_{timestamp}.csv'
            
            logger.info(f'Exported {len(staff_performance)} staff members to CSV: {filename}')
            return output, filename
            
        except Exception as e:
            logger.error(f'Error exporting staff performance to CSV: {str(e)}')
            raise


    @staticmethod
    def get_export_filename(format: str, report_type: str = 'requests') -> str:
        """Generate appropriate filename based on format and report type."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'csv':
            return f'{report_type}_{timestamp}.csv'
        elif format == 'pdf':
            return f'{report_type}_report_{timestamp}.pdf'
        else:
            return f'export_{timestamp}'
