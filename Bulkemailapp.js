import React, { useState } from "react";
import axios from "axios";

export default function BulkEmailApp() {
  const [file, setFile] = useState(null);
  const [candidates, setCandidates] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleFileUpload = (e) => {
    setFile(e.target.files[0]);
  };

  const uploadExcel = async () => {
    if (!file) return alert("Please upload an Excel file.");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post("http://localhost:8000/upload", formData);
      if (response.data.status === "success") {
        setCandidates(response.data.data);
      } else {
        alert(response.data.message);
      }
    } catch (error) {
      console.error(error);
      alert("Error uploading file.");
    }
  };

  const sendEmails = async () => {
    setLoading(true);
    try {
      const response = await axios.post("http://localhost:8000/send-emails", candidates);
      if (response.data.status === "success") {
        setResults(response.data.results);
      } else {
        alert(response.data.message);
      }
    } catch (error) {
      console.error(error);
      alert("Error sending emails.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Bulk Email Sender</h1>
      <div className="mb-4">
        <input type="file" accept=".xlsx" onChange={handleFileUpload} />
        <button className="ml-2 p-2 bg-blue-500 text-white rounded" onClick={uploadExcel}>
          Upload
        </button>
      </div>

      {candidates.length > 0 && (
        <div>
          <h2 className="text-xl font-bold mb-2">Candidates Preview</h2>
          <table className="table-auto w-full border">
            <thead>
              <tr>
                <th className="border px-2">Name</th>
                <th className="border px-2">Email</th>
                <th className="border px-2">Role</th>
              </tr>
            </thead>
            <tbody>
              {candidates.map((candidate, index) => (
                <tr key={index}>
                  <td className="border px-2">{candidate.Name}</td>
                  <td className="border px-2">{candidate.Email}</td>
                  <td className="border px-2">{candidate.Role}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <button
            className="mt-4 p-2 bg-green-500 text-white rounded"
            onClick={sendEmails}
            disabled={loading}
          >
            {loading ? "Sending Emails..." : "Send Emails"}
          </button>
        </div>
      )}

      {results.length > 0 && (
        <div className="mt-4">
          <h2 className="text-xl font-bold mb-2">Email Results</h2>
          <ul>
            {results.map((result, index) => (
              <li key={index}>
                {result.email}: {result.status}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
