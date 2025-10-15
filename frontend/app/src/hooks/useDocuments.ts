import { useContext } from "react";
import { DocumentContext } from "../contexts/DocumentContext";

const useDocuments = () => {
  const { documents, addDocument, removeDocument } = useContext(DocumentContext);

  return { documents, addDocument, removeDocument };
};

export default useDocuments;
