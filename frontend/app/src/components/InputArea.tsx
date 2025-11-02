import React, { useState, useRef } from 'react';
import { AiOutlineClose, AiOutlinePlus, AiOutlineSend as AiSend, AiOutlinePicture } from "react-icons/ai";
import useDocuments from '../hooks/useDocuments';

interface InputAreaProps {
  onSendMessage: (message: string, attachments?: File[]) => void;
  isLoading: boolean;
}

const InputArea: React.FC<InputAreaProps> = ({ onSendMessage, isLoading }) => {
  const [message, setMessage] = useState('');
  const [attachments, setAttachments] = useState<File[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);

  const { documents, addDocument, removeDocument } = useDocuments();
  
  const getUniqueName = (originalName: string, takenNames: Set<string>): string => {
    const dotIndex = originalName.lastIndexOf('.');
    const hasExt = dotIndex > 0;
    const base = hasExt ? originalName.slice(0, dotIndex) : originalName;
    const ext = hasExt ? originalName.slice(dotIndex) : '';
    let candidate = originalName;
    let counter = 1;
    while (takenNames.has(candidate)) {
      candidate = `${base} (${counter})${ext}`;
      counter += 1;
    }
    takenNames.add(candidate);
    return candidate;
  };

  // Helper function to generate base64 preview for images
  const generateImagePreview = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          // Create canvas to compress the image
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          
          // Set canvas dimensions (max 300px width/height for preview)
          const maxSize = 800;
          let { width, height } = img;
          
          if (width > height) {
            if (width > maxSize) {
              height = (height * maxSize) / width;
              width = maxSize;
            }
          } else {
            if (height > maxSize) {
              width = (width * maxSize) / height;
              height = maxSize;
            }
          }
          
          canvas.width = width;
          canvas.height = height;
          
          // Draw and compress image
          ctx?.drawImage(img, 0, 0, width, height);
          const compressedBase64 = canvas.toDataURL('image/jpeg', 0.9); // 90% quality
          resolve(compressedBase64);
        };
        img.onerror = reject;
        img.src = e.target?.result as string;
      };
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  };
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() || attachments.length > 0) {
      onSendMessage(message, attachments.length > 0 ? attachments : undefined);
      setMessage('');
      setAttachments([]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault();
      if (message.trim() || attachments.length > 0) {
        onSendMessage(message, attachments.length > 0 ? attachments : undefined);
        setMessage('');
        setAttachments([]);
      }
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    // Support both PDF and image files
    const supportedFiles = files.filter(file => 
      file.type === 'application/pdf' || 
      file.type.startsWith('image/')
    );
    const taken = new Set<string>([...attachments.map(f => f.name), ...documents.map(d => d.name)]);
    const renamed: File[] = supportedFiles.map(file => {
      const uniqueName = getUniqueName(file.name, taken);
      return uniqueName === file.name
        ? file
        : new File([file], uniqueName, { type: file.type, lastModified: file.lastModified });
    });
    setAttachments(prev => [...prev, ...renamed]);
    
    // Process each file and add to documents
    for (const file of renamed) {
      if (file.type.startsWith('image/')) {
        try {
          const preview = await generateImagePreview(file);
          addDocument({ 
            name: file.name, 
            file_path: file.name,
            preview: preview
          });
        } catch (error) {
          console.error('Error generating preview for', file.name, error);
          addDocument({ 
            name: file.name, 
            file_path: file.name
          });
        }
      } else {
        addDocument({ 
          name: file.name, 
          file_path: file.name
        });
      }
    }
  };

  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    // Only allow image files
    const imageFiles = files.filter(file => file.type.startsWith('image/'));
    const taken = new Set<string>([...attachments.map(f => f.name), ...documents.map(d => d.name)]);
    const renamed: File[] = imageFiles.map(file => {
      const uniqueName = getUniqueName(file.name, taken);
      return uniqueName === file.name
        ? file
        : new File([file], uniqueName, { type: file.type, lastModified: file.lastModified });
    });
    setAttachments(prev => [...prev, ...renamed]);
    
    // Process each image file and add to documents with preview
    for (const file of renamed) {
      try {
        const preview = await generateImagePreview(file);
        addDocument({ 
          name: file.name, 
          file_path: file.name,
          preview: preview
        });
      } catch (error) {
        console.error('Error generating preview for', file.name, error);
        addDocument({ 
          name: file.name, 
          file_path: file.name
        });
      }
    }
  };

  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
    
    const documentToRemove = documents[index];
    removeDocument(documentToRemove);
  };

  return (
    <div className="border-t border-gray-200 p-4">
      {/* Attachments Preview */}
      {documents.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {documents.map((document, index) => {
            const isImage = document.name.match(/\.(jpg|jpeg|png|gif|bmp|tiff|webp)$/i);
            return (
              <div
                key={`${document.file_path}-${index}`}
                className="flex items-center space-x-2 bg-gray-100 rounded-lg px-3 py-2 text-sm"
              >
                {isImage ? (
                  <AiOutlinePicture className="w-4 h-4 text-blue-500" />
                ) : (
                  <span className="text-red-500 text-xs font-bold">PDF</span>
                )}
                <span className="text-gray-600 truncate max-w-32">{document.name}</span>
                <button
                  onClick={() => removeAttachment(index)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <AiOutlineClose className="w-4 h-4" />
                </button>
              </div>
            );
          })}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Input Field */}
        <div className="flex items-end space-x-3">
          <div className="flex-1">
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask whatever you want...."
              className="w-full p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              rows={3}
              maxLength={1000}
              disabled={isLoading}
            />
            <div className="flex justify-between items-center mt-2">
              <div className="flex space-x-4">
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center space-x-1 text-gray-500 hover:text-gray-700 text-sm"
                  disabled={isLoading}
                >
                  <AiOutlinePlus className="w-4 h-4" />
                  <span>Add Files</span>
                </button>
                <button
                  type="button"
                  onClick={() => imageInputRef.current?.click()}
                  className="flex items-center space-x-1 text-gray-500 hover:text-gray-700 text-sm"
                  disabled={isLoading}
                >
                  <AiOutlinePicture className="w-4 h-4" />
                  <span>Add Images</span>
                </button>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-xs text-gray-400">
                  {message.length}/1000
                </span>
                <button
                  type="submit"
                  disabled={isLoading || (!message.trim() && attachments.length === 0)}
                  className="w-8 h-8 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-full flex items-center justify-center hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                >
                  <AiSend className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Web Search Dropdown */}
        <div className="flex justify-end">
          <select className="text-sm text-gray-600 bg-transparent border-none focus:outline-none">
            <option>All Web</option>
            <option>Recent</option>
            <option>Images</option>
            <option>Videos</option>
          </select>
        </div>
      </form>

      {/* Hidden File Inputs */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.jpg,.jpeg,.png,.bmp,.gif,.tiff,.webp"
        multiple
        onChange={handleFileUpload}
        className="hidden"
      />
      <input
        ref={imageInputRef}
        type="file"
        accept="image/*"
        multiple
        onChange={handleImageUpload}
        className="hidden"
      />
    </div>
  );
};

export default InputArea;
