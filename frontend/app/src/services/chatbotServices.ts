import { API_BASE_URL } from '../../config/const';

// TypeScript interfaces for API responses
interface HealthResponse {
  status: string;
  service: string;
}

interface ProcessPDFResponse {
  status: string;
  processed_files: string;
  total_chunks?: number;
}

interface ChatResponse {
  answer: string;
  chat_history: [string, string][];
  confidence?: number;
  source_files?: string[];
}

interface MemoryStatus {
  processed_files: string[];
  total_chunks: number;
  total_documents: number;
}

interface ClearMemoryResponse {
  message: string;
  status: string;
}

interface ChatRequest {
  query: string;
  chat_history?: [string, string][];
}

interface DocumentInfo {
  filename: string;
  file_type: string;
  chunks_count: number;
  heading: string;
  preview: string;
  file_size?: number;         // File size in bytes (RAG v2.0)
  created_at?: string;        // ISO timestamp (RAG v2.0)
  status?: string;            // Processing status: pending, processed, failed (RAG v2.0)
}

interface DocumentsListResponse {
  documents: DocumentInfo[];
  total_documents: number;
}

interface DeleteDocumentResponse {
  message: string;
  status: string;
}

interface ApiError {
  detail: string;
}

// Base configuration
const CHATBOT_API_BASE_URL = `${API_BASE_URL}/chatbot`;

// Utility function for error handling
const handleApiError = async (response: Response): Promise<never> => {
  let errorMessage = 'An unexpected error occurred';
  
  try {
    const errorData: ApiError = await response.json();
    errorMessage = errorData.detail;
  } catch {
    errorMessage = `HTTP ${response.status}: ${response.statusText}`;
  }
  
  throw new Error(errorMessage);
};

const chatbotServices = {
  /**
   * Check if the chatbot service is running and healthy
   * @returns Promise<HealthResponse>
   */
  async checkHealth(): Promise<HealthResponse> {
    try {
      const response = await fetch(`${CHATBOT_API_BASE_URL}/health`);
      
      if (!response.ok) {
        await handleApiError(response);
      }
      
      return await response.json();
    } catch (error) {
      throw new Error(`Health check failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  /**
   * Upload and process a document (PDF or image)
   * @param file - The document file to upload (PDF or image)
   * @returns Promise<ProcessPDFResponse>
   */
  async uploadDocument(file: File): Promise<ProcessPDFResponse> {
    try {
      // Validate file type
      const supportedTypes = [
        'application/pdf',
        'image/jpeg',
        'image/jpg', 
        'image/png',
        'image/bmp',
        'image/gif',
        'image/tiff',
        'image/webp'
      ];

      if (!supportedTypes.includes(file.type)) {
        throw new Error('Unsupported file type. Supported formats: PDF, JPG, PNG, BMP, GIF, TIFF, WEBP');
      }

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${CHATBOT_API_BASE_URL}/upload-document`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        await handleApiError(response);
      }

      return await response.json();
    } catch (error) {
      throw new Error(`Document upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  /**
   * Upload and process a PDF file (legacy method for backward compatibility)
   * @param file - The PDF file to upload
   * @returns Promise<ProcessPDFResponse>
   */
  async uploadPDF(file: File): Promise<ProcessPDFResponse> {
    try {
      // Validate file type
      if (file.type !== 'application/pdf') {
        throw new Error('Only PDF files are supported for this endpoint. Use uploadDocument for images.');
      }

      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${CHATBOT_API_BASE_URL}/upload-pdf`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        await handleApiError(response);
      }

      return await response.json();
    } catch (error) {
      throw new Error(`PDF upload failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  /**
   * Send a chat message to the chatbot
   * @param query - The question to ask
   * @param chatHistory - Optional chat history for context
   * @returns Promise<ChatResponse>
   */
  async chat(query: string, chatHistory: [string, string][] = []): Promise<ChatResponse> {
    try {
      if (!query.trim()) {
        throw new Error('Query cannot be empty');
      }

      const requestBody: ChatRequest = {
        query: query.trim(),
        chat_history: chatHistory,
      };

      const response = await fetch(`${CHATBOT_API_BASE_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (!response.ok) {
        await handleApiError(response);
      }

      return await response.json();
    } catch (error) {
      throw new Error(`Chat request failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  /**
   * Get the current memory status of the chatbot
   * @returns Promise<MemoryStatus>
   */
  async getMemoryStatus(): Promise<MemoryStatus> {
    try {
      const response = await fetch(`${CHATBOT_API_BASE_URL}/memory/status`);

      if (!response.ok) {
        await handleApiError(response);
      }

      return await response.json();
    } catch (error) {
      throw new Error(`Memory status request failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  /**
   * Clear all memory from the chatbot
   * @returns Promise<ClearMemoryResponse>
   */
  async clearMemory(): Promise<ClearMemoryResponse> {
    try {
      const response = await fetch(`${CHATBOT_API_BASE_URL}/memory`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        await handleApiError(response);
      }

      return await response.json();
    } catch (error) {
      throw new Error(`Clear memory request failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  /**
   * Get confidence level description
   * @param confidence - Confidence score (0-1)
   * @returns String description of confidence level
   */
  getConfidenceLevel(confidence?: number): string {
    if (confidence === undefined || confidence === null) {
      return 'Unknown';
    }
    
    if (confidence < 0.4) {
      return 'Low (may not be closely related)';
    } else if (confidence <= 0.65) {
      return 'Medium';
    } else {
      return 'High';
    }
  },

  /**
   * Format confidence as percentage
   * @param confidence - Confidence score (0-1)
   * @returns Formatted percentage string
   */
  formatConfidence(confidence?: number): string {
    if (confidence === undefined || confidence === null) {
      return 'N/A';
    }
    
    return `${Math.round(confidence * 100)}%`;
  },

  /**
   * Get the list of all processed documents
   * @returns Promise<DocumentsListResponse>
   */
  async getDocuments(): Promise<DocumentsListResponse> {
    try {
      const response = await fetch(`${CHATBOT_API_BASE_URL}/memorable-documents`);

      if (!response.ok) {
        await handleApiError(response);
      }

      return await response.json();
    } catch (error) {
      throw new Error(`Get documents failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },

  /**
   * Delete a specific document by filename
   * @param filename - The filename of the document to delete
   * @returns Promise<DeleteDocumentResponse>
   */
  async deleteDocument(filename: string): Promise<DeleteDocumentResponse> {
    try {
      if (!filename.trim()) {
        throw new Error('Filename cannot be empty');
      }

      // URL encode the filename to handle special characters
      const encodedFilename = encodeURIComponent(filename);

      const response = await fetch(`${CHATBOT_API_BASE_URL}/memorable-documents/${encodedFilename}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        await handleApiError(response);
      }

      return await response.json();
    } catch (error) {
      throw new Error(`Delete document failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  },
};

export default chatbotServices;

// Export types for use in other components
export type {
  HealthResponse,
  ProcessPDFResponse,
  ChatResponse,
  MemoryStatus,
  ClearMemoryResponse,
  ChatRequest,
  DocumentInfo,
  DocumentsListResponse,
  DeleteDocumentResponse,
  ApiError,
};