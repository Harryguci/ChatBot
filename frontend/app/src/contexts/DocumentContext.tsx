import { createContext, useState } from "react";
import type { IDocument } from "../pages/ChatBotPage";

export const DocumentContext = createContext<{
  documents: IDocument[];
  addDocument: (document: IDocument) => void;
  removeDocument: (document: IDocument) => void;
}>({
  documents: [],
  addDocument: () => {},
  removeDocument: () => {},
});

export const DocumentProvider = ({ children }: { children: React.ReactNode }) => {
  const [documents, setDocuments] = useState<IDocument[]>([]);

  const addDocument = (document: IDocument) => {
    setDocuments([...documents, document]);
  };

  const removeDocument = (document: IDocument) => {
    setDocuments(documents.filter((d) => d.file_path !== document.file_path));
  };

  return (
    <DocumentContext.Provider value={{ documents, addDocument, removeDocument }}>
      {children}
    </DocumentContext.Provider>
  );
};