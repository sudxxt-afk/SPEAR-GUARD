import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';

export interface ExportOptions {
    filename?: string;
    format?: 'png' | 'pdf';
    quality?: number;
}

/**
 * Export a DOM element as PNG image
 */
export const exportToPNG = async (
    elementId: string,
    options: ExportOptions = {}
): Promise<void> => {
    const { filename = 'chart', quality = 1.0 } = options;

    const element = document.getElementById(elementId);
    if (!element) {
        throw new Error(`Element with id "${elementId}" not found`);
    }

    try {
        const canvas = await html2canvas(element, {
            backgroundColor: '#1e293b', // slate-800
            scale: 2, // Higher resolution
            logging: false,
        });

        // Convert to blob and download
        canvas.toBlob((blob: Blob | null) => {
            if (blob) {
                const url = URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = url;
                link.download = `${filename}.png`;
                link.click();
                URL.revokeObjectURL(url);
            }
        }, 'image/png', quality);
    } catch (error) {
        console.error('Error exporting to PNG:', error);
        throw error;
    }
};

/**
 * Export a DOM element as PDF
 */
export const exportToPDF = async (
    elementId: string,
    options: ExportOptions = {}
): Promise<void> => {
    const { filename = 'chart' } = options;

    const element = document.getElementById(elementId);
    if (!element) {
        throw new Error(`Element with id "${elementId}" not found`);
    }

    try {
        const canvas = await html2canvas(element, {
            backgroundColor: '#1e293b',
            scale: 2,
            logging: false,
        });

        const imgData = canvas.toDataURL('image/png');
        const pdf = new jsPDF({
            orientation: canvas.width > canvas.height ? 'landscape' : 'portrait',
            unit: 'px',
            format: [canvas.width, canvas.height],
        });

        pdf.addImage(imgData, 'PNG', 0, 0, canvas.width, canvas.height);
        pdf.save(`${filename}.pdf`);
    } catch (error) {
        console.error('Error exporting to PDF:', error);
        throw error;
    }
};

/**
 * Export multiple charts to a single PDF
 */
export const exportMultipleToPDF = async (
    elementIds: string[],
    filename: string = 'dashboard-report'
): Promise<void> => {
    const pdf = new jsPDF({
        orientation: 'portrait',
        unit: 'mm',
        format: 'a4',
    });

    for (let i = 0; i < elementIds.length; i++) {
        const element = document.getElementById(elementIds[i]);
        if (!element) continue;

        try {
            const canvas = await html2canvas(element, {
                backgroundColor: '#1e293b',
                scale: 2,
                logging: false,
            });

            const imgData = canvas.toDataURL('image/png');
            const imgWidth = 190; // A4 width in mm minus margins
            const imgHeight = (canvas.height * imgWidth) / canvas.width;

            if (i > 0) {
                pdf.addPage();
            }

            pdf.addImage(imgData, 'PNG', 10, 10, imgWidth, imgHeight);
        } catch (error) {
            console.error(`Error exporting element ${elementIds[i]}:`, error);
        }
    }

    pdf.save(`${filename}.pdf`);
};
