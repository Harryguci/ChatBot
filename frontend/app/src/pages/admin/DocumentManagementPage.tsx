import { useState, useEffect, useCallback } from 'react';
import chatbotServices, { type DocumentInfo } from '../../services/chatbotServices';

const DocumentManagementPage = () => {
    const [documents, setDocuments] = useState<DocumentInfo[]>([]);
    const [loading, setLoading] = useState<boolean>(true);
    const [uploading, setUploading] = useState<boolean>(false);
    const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [replaceMode, setReplaceMode] = useState<string | null>(null);

    const showMessage = (type: 'success' | 'error', text: string) => {
        setMessage({ type, text });
        setTimeout(() => setMessage(null), 5000);
    };

    const loadDocuments = useCallback(async () => {
        try {
            setLoading(true);
            const response = await chatbotServices.getDocuments();
            setDocuments(response.documents);
        } catch (error) {
            showMessage('error', `Failed to load documents: ${error instanceof Error ? error.message : 'Unknown error'}`);
        } finally {
            setLoading(false);
        }
    }, []);

    // Load documents on mount
    useEffect(() => {
        loadDocuments();
    }, [loadDocuments]);

    const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        if (file) {
            setSelectedFile(file);
            setMessage(null);
        }
    };

    const handleUpload = async () => {
        if (!selectedFile) {
            showMessage('error', 'Please select a file first');
            return;
        }

        try {
            setUploading(true);
            
            // If in replace mode, delete the old document first
            if (replaceMode) {
                await chatbotServices.deleteDocument(replaceMode);
            }

            // Upload the new document
            await chatbotServices.uploadDocument(selectedFile);
            
            showMessage('success', `Document "${selectedFile.name}" uploaded successfully${replaceMode ? ' and replaced' : ''}`);
            
            // Reset state
            setSelectedFile(null);
            setReplaceMode(null);
            if (document.getElementById('fileInput') as HTMLInputElement) {
                (document.getElementById('fileInput') as HTMLInputElement).value = '';
            }
            
            // Reload documents list
            await loadDocuments();
        } catch (error) {
            showMessage('error', `Upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        } finally {
            setUploading(false);
        }
    };

    const handleDelete = async (filename: string) => {
        if (!confirm(`Are you sure you want to delete "${filename}"? This action cannot be undone.`)) {
            return;
        }

        try {
            await chatbotServices.deleteDocument(filename);
            showMessage('success', `Document "${filename}" deleted successfully`);
            await loadDocuments();
        } catch (error) {
            showMessage('error', `Delete failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
        }
    };

    const handleReplace = (filename: string) => {
        setReplaceMode(filename);
        setMessage({ type: 'success', text: `Now upload a new file to replace "${filename}"` });
    };

    const cancelReplace = () => {
        setReplaceMode(null);
        setSelectedFile(null);
        setMessage(null);
        if (document.getElementById('fileInput') as HTMLInputElement) {
            (document.getElementById('fileInput') as HTMLInputElement).value = '';
        }
    };

    return (
        <div className="p-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-6">Document Management</h1>
            
            {/* Message Display */}
            {message && (
                <div className={`mb-4 p-4 rounded-lg ${message.type === 'success' ? 'bg-green-50 text-green-800 border border-green-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
                    {message.text}
                </div>
            )}

            {/* Upload Section */}
            <div className="bg-white rounded-lg shadow p-6 mb-6">
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                    {replaceMode ? `Replace Document: ${replaceMode}` : 'Upload New Document'}
                </h2>
                
                {replaceMode && (
                    <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
                        <p className="text-sm text-yellow-800">
                            You are in replace mode. Upload a new file to replace "{replaceMode}".
                        </p>
                        <button
                            onClick={cancelReplace}
                            className="mt-2 text-sm text-yellow-700 hover:text-yellow-900 underline"
                        >
                            Cancel Replace
                        </button>
                    </div>
                )}

                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                            Select Document (PDF or Image)
                        </label>
                        <input
                            id="fileInput"
                            type="file"
                            accept=".pdf,image/jpeg,image/jpg,image/png,image/bmp,image/gif,image/tiff,image/webp"
                            onChange={handleFileSelect}
                            className="block w-full text-sm text-gray-500
                                file:mr-4 file:py-2 file:px-4
                                file:rounded-lg file:border-0
                                file:text-sm file:font-semibold
                                file:bg-blue-50 file:text-blue-700
                                hover:file:bg-blue-100"
                        />
                        {selectedFile && (
                            <p className="mt-2 text-sm text-gray-600">
                                Selected: <span className="font-medium">{selectedFile.name}</span>
                            </p>
                        )}
                    </div>

                    <button
                        onClick={handleUpload}
                        disabled={!selectedFile || uploading}
                        className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
                    >
                        {uploading ? 'Uploading...' : replaceMode ? 'Replace Document' : 'Upload Document'}
                    </button>
                </div>
            </div>

            {/* Documents List */}
            <div className="bg-white rounded-lg shadow p-6">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-semibold text-gray-900">
                        Documents ({documents.length})
                    </h2>
                    <button
                        onClick={loadDocuments}
                        className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                    >
                        Refresh
                    </button>
                </div>

                {loading ? (
                    <div className="text-center py-8">
                        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
                        <p className="mt-2 text-gray-600">Loading documents...</p>
                    </div>
                ) : documents.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                        No documents uploaded yet.
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Filename
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Type
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Chunks
                                    </th>
                                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Preview
                                    </th>
                                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                                        Actions
                                    </th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {documents.map((doc, index) => (
                                    <tr key={index} className="hover:bg-gray-50">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="text-sm font-medium text-gray-900">{doc.filename}</div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                                                {doc.file_type}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                                            {doc.chunks_count}
                                        </td>
                                        <td className="px-6 py-4">
                                            <div className="text-sm text-gray-500 max-w-md truncate">
                                                {doc.preview}
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                            <button
                                                onClick={() => handleReplace(doc.filename)}
                                                className="text-blue-600 hover:text-blue-900 mr-4"
                                            >
                                                Replace
                                            </button>
                                            <button
                                                onClick={() => handleDelete(doc.filename)}
                                                className="text-red-600 hover:text-red-900"
                                            >
                                                Delete
                                            </button>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};

export default DocumentManagementPage;