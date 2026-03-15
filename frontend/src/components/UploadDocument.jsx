import React, { useState, useEffect } from "react";
import { uploadDocument, listDocuments } from "../api";

const UploadDocument = ({ onUploaded }) => {
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [docCount, setDocCount] = useState(0);

  const fetchDocuments = async () => {
    try {
      const docs = await listDocuments();
      setDocCount(docs.length);
    } catch {}
  };

  useEffect(() => { fetchDocuments(); }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
    try {
      setUploading(true);
      await uploadDocument(file);
      setFile(null);
      await fetchDocuments();
      if (onUploaded) onUploaded();
    } catch (err) {
      console.error(err);
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="bg-white p-4 rounded shadow mb-4">
      <h2 className="font-semibold mb-2">Upload PDF</h2>
      <form onSubmit={handleSubmit} className="flex items-center gap-3">
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files[0] || null)}
          className="block w-full text-sm text-gray-700"
        />
        <button
          type="submit"
          disabled={!file || uploading}
          className="px-4 py-2 rounded bg-blue-600 text-white text-sm hover:bg-blue-700 disabled:bg-gray-300"
        >
          {uploading ? "Uploading..." : "Upload"}
        </button>
      </form>
      {docCount > 0 && (
        <p className="mt-2 text-sm text-gray-600">
          {docCount} document{docCount > 1 ? "s" : ""} uploaded
        </p>
      )}
    </div>
  );
};

export default UploadDocument;
