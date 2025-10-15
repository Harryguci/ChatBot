import React, { useState } from "react";
import Sidebar from "../components/Sidebar";
import ChatArea from "../components/ChatArea";
import InputArea from "../components/InputArea";
import DocumentsTab from "../components/DocumentsTab";
import { useChat } from "../hooks/useChat";
import { DocumentProvider } from "../contexts/DocumentContext";

export interface IDocument {
  name: string;
  file_path: string;
  preview?: string; // base64 of the image
}

const ChatBotPage: React.FC = () => {
  const { messages, isLoading, error, sendMessage, clearChat } = useChat();
  const [showPrompts, setShowPrompts] = useState(messages.length === 0);
  const [showDocuments, setShowDocuments] = useState(false);
  const handleSendMessage = (message: string, attachments?: File[]) => {
    setShowPrompts(false);
    sendMessage(message, attachments);
  };

  // const handlePromptSelect = (prompt: string) => {
  //   setShowPrompts(false);
  //   sendMessage(prompt);
  // };

  const handleNewChat = () => {
    clearChat();
    setShowPrompts(true);
  };

  const handleRefreshPrompts = () => {
    setShowPrompts(true);
  };

  function handleOpenDocuments(): void {
    setShowDocuments(true);
  }

  function handleCloseDocuments(): void {
    setShowDocuments(false);
  }

  return (
    <DocumentProvider>
      <div className="h-screen flex bg-gray-50">
        {/* Sidebar */}
        <Sidebar
          onNewChat={handleNewChat}
          onSearch={() => console.log("Search clicked")}
          onHistory={() => console.log("History clicked")}
          onSettings={() => console.log("Settings clicked")}
          onDocuments={() => handleOpenDocuments()}
        />

        {/* Main Content */}
        <div className="flex-1 flex flex-col">
          {showDocuments ? (
            /* Documents Tab */
            <DocumentsTab onClose={handleCloseDocuments} />
          ) : (
            <>
              {/* Chat Area */}
              <ChatArea messages={messages} isLoading={isLoading} />

              {/* Prompt Cards (shown when no messages) */}
              {showPrompts && messages.length === 0 && (
                <div className="px-8 pb-4">
                  {/* <PromptCards onPromptSelect={handlePromptSelect} /> */}
                  <div className="flex justify-center">
                    <button
                      onClick={handleRefreshPrompts}
                      className="flex items-center space-x-2 text-gray-500 hover:text-gray-700 text-sm"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                        />
                      </svg>
                      <span>Refresh Prompts</span>
                    </button>
                  </div>
                </div>
              )}

              {/* Error Display */}
              {error && (
                <div className="mx-6 mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded-lg">
                  {error}
                </div>
              )}

              {/* Input Area */}
              <InputArea onSendMessage={handleSendMessage} isLoading={isLoading} />
            </>
          )}
        </div>
      </div>
    </DocumentProvider>
  );
};

export default ChatBotPage;
