import React, { useRef, useEffect } from "react";
import type { Message } from "../hooks/useChat";
import useDocuments from "../hooks/useDocuments";

interface ChatAreaProps {
  messages: Message[];
  isLoading: boolean;
}

const ChatArea: React.FC<ChatAreaProps> = ({ messages, isLoading }) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { documents } = useDocuments();

  // Helper function to check if a file is an image
  const isImageFile = (filename: string): boolean => {
    const imageExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg'];
    const extension = filename.toLowerCase().substring(filename.lastIndexOf('.'));
    return imageExtensions.includes(extension);
  };

  // Helper function to get document data by filename
  const getDocumentByFilename = (filename: string) => {
    return documents.find(doc => doc.name === filename);
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">
            Hi there,{" "}
            <span className="bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
              User
            </span>
          </h1>
          <p className="text-gray-500 text-sm">
            Upload your documents and ask questions about them.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${
            message.role === "user" ? "justify-end" : "justify-start"
          }`}
        >
          <div
            className={`${message.role === "user" ? "max-w-xs lg:max-w-md" : "max-w-sm lg:max-w-lg"} px-4 py-2 rounded-lg ${
              message.role === "user"
                ? "bg-gradient-to-r from-purple-600 to-pink-600 text-white"
                : "bg-gray-100 text-gray-800"
            }`}
          >
            <p
              className="text-sm"
              dangerouslySetInnerHTML={{ __html: message.content }}
            />
            
            {/* Display source files if they are images */}
            {message.role === "assistant" && message.source_files && message.source_files.length > 0 && (
              <div className="mt-2 space-y-2">
                {message.source_files
                  .filter(filename => isImageFile(filename))
                  .map((filename, index) => {
                    const document = getDocumentByFilename(filename);
                    if (document) {
                      return (
                        <div key={index} className="border rounded-lg p-2 bg-white">
                          <p className="text-xs text-gray-600 mb-1">Source: {filename}</p>
                          <img
                            src={document.preview || document.file_path}
                            alt={filename}
                            className="w-auto h-[600px] rounded object-contain"
                            onError={(e) => {
                              const target = e.target as HTMLImageElement;
                              target.style.display = 'none';
                            }}
                          />
                        </div>
                      );
                    }
                    return null;
                  })}
              </div>
            )}
            
            <p
              className={`text-xs mt-1 ${
                message.role === "user" ? "text-purple-100" : "text-gray-500"
              }`}
            >
              {message.timestamp.toLocaleTimeString()}
            </p>
          </div>
        </div>
      ))}

      {isLoading && (
        <div className="flex justify-start">
          <div className="bg-gray-100 text-gray-800 max-w-xs lg:max-w-md px-4 py-2 rounded-lg">
            <div className="flex items-center space-x-2">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.1s" }}
                ></div>
                <div
                  className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                  style={{ animationDelay: "0.2s" }}
                ></div>
              </div>
              <span className="text-xs text-gray-500">AI is thinking...</span>
            </div>
          </div>
        </div>
      )}

      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatArea;
