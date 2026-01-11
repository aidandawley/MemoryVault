import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";

type Props = {
  onUploaded?: (result: any) => void;
};

export default function UploadDropzone({ onUploaded }: Props) {
  const [status, setStatus] = useState<string>("");

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const file = acceptedFiles[0];
    if (!file) return;

    try {
      setStatus("Uploading...");

      const form = new FormData();
      form.append("file", file);

      // Change URL if your backend prefix differs
      const res = await fetch("http://127.0.0.1:8000/media/upload", {
        method: "POST",
        body: form,
      });

      if (!res.ok) throw new Error(await res.text());

      const data = await res.json();
      setStatus("Done");
      onUploaded?.(data);
    } catch (e: any) {
      setStatus(`Error: ${e.message ?? "upload failed"}`);
    }
  }, [onUploaded]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: false,
   
    accept: {
      "video/*": [],
      "image/*": [],
    },
  });

  return (
    <div
      {...getRootProps()}
      style={{
        border: "2px dashed #999",
        borderRadius: 12,
        padding: 18,
        textAlign: "center",
        cursor: "pointer",
        marginBottom: 16,
      }}
    >
      <input {...getInputProps()} />
      <div style={{ fontWeight: 700 }}>
        {isDragActive ? "Drop it here…" : "Drag & drop a photo/video here"}
      </div>
      <div style={{ opacity: 0.75, marginTop: 6 }}>or click to select</div>
      {status && <div style={{ marginTop: 10, fontSize: 14 }}>{status}</div>}
    </div>
  );
}
