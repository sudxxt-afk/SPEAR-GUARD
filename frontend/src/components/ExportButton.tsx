import React from 'react';
import { Download, FileImage, FileText } from 'lucide-react';
import { exportToPNG, exportToPDF } from '../utils/exportChart';

interface ExportButtonProps {
    elementId: string;
    filename: string;
    className?: string;
}

export const ExportButton: React.FC<ExportButtonProps> = ({
    elementId,
    filename,
    className = ''
}) => {
    const [isExporting, setIsExporting] = React.useState(false);
    const [showMenu, setShowMenu] = React.useState(false);

    const handleExport = async (format: 'png' | 'pdf') => {
        setIsExporting(true);
        setShowMenu(false);

        try {
            if (format === 'png') {
                await exportToPNG(elementId, { filename });
            } else {
                await exportToPDF(elementId, { filename });
            }
        } catch (error) {
            console.error('Export failed:', error);
            alert('Ошибка при экспорте. Попробуйте еще раз.');
        } finally {
            setIsExporting(false);
        }
    };

    return (
        <div className={`relative ${className}`}>
            <button
                onClick={() => setShowMenu(!showMenu)}
                disabled={isExporting}
                className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
                <Download className="w-4 h-4" />
                <span className="text-sm">
                    {isExporting ? 'Экспорт...' : 'Экспорт'}
                </span>
            </button>

            {showMenu && !isExporting && (
                <div className="absolute right-0 top-full mt-2 bg-slate-700 rounded-lg shadow-xl border border-slate-600 overflow-hidden z-10 min-w-[150px]">
                    <button
                        onClick={() => handleExport('png')}
                        className="w-full flex items-center gap-2 px-4 py-2 hover:bg-slate-600 text-white transition-colors text-left"
                    >
                        <FileImage className="w-4 h-4" />
                        <span className="text-sm">PNG</span>
                    </button>
                    <button
                        onClick={() => handleExport('pdf')}
                        className="w-full flex items-center gap-2 px-4 py-2 hover:bg-slate-600 text-white transition-colors text-left"
                    >
                        <FileText className="w-4 h-4" />
                        <span className="text-sm">PDF</span>
                    </button>
                </div>
            )}

            {/* Backdrop to close menu */}
            {showMenu && (
                <div
                    className="fixed inset-0 z-0"
                    onClick={() => setShowMenu(false)}
                />
            )}
        </div>
    );
};
