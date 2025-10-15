import { useState, useCallback } from 'react';
import chatbotServices, { type ChatResponse } from '../services/chatbotServices';

export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  confidence?: number;
  source_files?: string[];
}

export interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
}

export const useChat = () => {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    error: null,
  });

  const sendMessage = useCallback(async (content: string, attachments?: File[]) => {
    console.log('sendMessage', content, attachments);
    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      role: 'user',
      timestamp: new Date(),
    };

    setChatState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage],
      isLoading: true,
      error: null,
    }));

    try {
      // Handle document attachments first (PDF or images)
      if (attachments && attachments.length > 0) {
        for (const file of attachments) {
          // Check if it's a supported file type
          const isPDF = file.type === 'application/pdf';
          const isImage = file.type.startsWith('image/');
          
          if (isPDF || isImage) {
            await chatbotServices.uploadDocument(file);
          }
        }
      }

      // Convert messages to chat history format for API
      const chatHistory: [string, string][] = chatState.messages
        .reduce<[string, string][]>((acc, msg, index) => {
          if (msg.role === 'user' && index + 1 < chatState.messages.length) {
            const nextMsg = chatState.messages[index + 1];
            if (nextMsg.role === 'assistant') {
              acc.push([msg.content, nextMsg.content]);
            }
          }
          return acc;
        }, []);

      // Send chat request to actual API
      const response: ChatResponse = await chatbotServices.chat(content, chatHistory);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.answer,
        role: 'assistant',
        timestamp: new Date(),
        confidence: response.confidence,
        source_files: response.source_files,
      };

      setChatState(prev => ({
        ...prev,
        messages: [...prev.messages, assistantMessage],
        isLoading: false,
      }));
    } catch (error) {
      setChatState(prev => ({
        ...prev,
        isLoading: false,
        error: error instanceof Error ? error.message : 'An error occurred',
      }));
    }
  }, [chatState.messages]);

  const clearChat = useCallback(() => {
    setChatState({
      messages: [],
      isLoading: false,
      error: null,
    });
  }, []);

  const clearMemory = useCallback(async () => {
    try {
      await chatbotServices.clearMemory();
      // Optionally clear chat as well when memory is cleared
      clearChat();
    } catch (error) {
      setChatState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to clear memory',
      }));
    }
  }, [clearChat]);

  const getMemoryStatus = useCallback(async () => {
    try {
      return await chatbotServices.getMemoryStatus();
    } catch (error) {
      setChatState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Failed to get memory status',
      }));
      return null;
    }
  }, []);

  const checkHealth = useCallback(async () => {
    try {
      return await chatbotServices.checkHealth();
    } catch (error) {
      setChatState(prev => ({
        ...prev,
        error: error instanceof Error ? error.message : 'Health check failed',
      }));
      return null;
    }
  }, []);

  return {
    ...chatState,
    sendMessage,
    clearChat,
    clearMemory,
    getMemoryStatus,
    checkHealth,
  };
};
