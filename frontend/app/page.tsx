"use client";

import React, { useState, useEffect } from 'react';
import { UploadCloud, FileText, Image as ImageIcon, Activity, CheckCircle2, Database, Cpu, Shield, Landmark, DollarSign, Library, X, FileCode, ExternalLink, ChevronLeft } from 'lucide-react';

type DatasetFile = { name: string, path: string, type: string, size: string };

export default function FinsuranceDashboard() {
  const [contractFile, setContractFile] = useState<File | null>(null);
  const [billFiles, setBillFiles] = useState<FileList | null>(null);
  const [insuranceType, setInsuranceType] = useState('health');
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [processStatus, setProcessStatus] = useState<string | null>(null);
  
  // Datasets Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [datasetCategory, setDatasetCategory] = useState<'All' | 'Health' | 'Auto' | 'Homeowners' | 'Life & Other' | 'CSV'>('All');
  const [datasetReferences, setDatasetReferences] = useState<Record<string, DatasetFile[]>>({});
  const [viewingFile, setViewingFile] = useState<{name: string, url: string} | null>(null);

  // Fetch real dataset list from backend API
  useEffect(() => {
    if (isModalOpen && Object.keys(datasetReferences).length === 0) {
      fetch('/api/documents')
        .then(res => res.json())
        .then(data => setDatasetReferences(data))
        .catch(err => console.error("Failed to load datasets:", err));
    }
  }, [isModalOpen, datasetReferences]);

  const getFilteredDatasets = (): DatasetFile[] => {
    if (datasetCategory === 'All') {
      return Object.values(datasetReferences).flat();
    }
    return datasetReferences[datasetCategory] || [];
  };

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!contractFile || !billFiles) return;

    setIsAnalyzing(true);
    setProcessStatus(null);

    // Mocking the connection latency before backend implementation
    setTimeout(() => {
      setIsAnalyzing(false);
      setProcessStatus("Files ingested. Backend integration pending.");
    }, 2000);
  };

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-sans selection:bg-emerald-500 selection:text-white">
      {/* FinTech / Tech Vibe Header */}
      <header className="bg-slate-950 border-b border-slate-800 px-8 py-5 flex items-center justify-between sticky top-0 z-10 shadow-md">
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-12 h-12 mr-2">
            {/* Impressive Symbol Icon Start */}
            <div className="absolute inset-0 bg-emerald-500 blur-xl opacity-20 rounded-full animate-pulse"></div>
            <div className="absolute inset-0 border-2 border-emerald-500/30 rounded-lg transform rotate-45 transition-transform duration-500 hover:rotate-90"></div>
            <div className="absolute inset-0 border-2 border-teal-400/30 rounded-lg transform -rotate-45"></div>
            <Shield className="w-7 h-7 text-emerald-400 relative z-10" strokeWidth={1.5} />
            <DollarSign className="w-3.5 h-3.5 text-teal-200 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" strokeWidth={2.5} />
            {/* Impressive Symbol Icon End */}
          </div>
          <h1 className="text-3xl font-extrabold tracking-tighter uppercase text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-emerald-500">
            Finsurance
          </h1>
        </div>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-2 text-xs font-semibold text-slate-400 bg-slate-800 px-3 py-1.5 rounded-full border border-slate-700">
            <Database className="w-3 h-3 text-emerald-400" />
            Secure Vault
          </span>
          <div className="text-sm font-medium text-slate-400 hidden md:block">AI Auditor Dashboard</div>
        </div>
      </header>
      
      <main className="max-w-6xl mx-auto p-4 md:p-8 grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Upload Form Section */}
        <section className="bg-slate-800/50 rounded-2xl border border-slate-700 p-6 md:p-8 shadow-xl backdrop-blur-sm relative overflow-hidden">
          {/* Subtle grid background effect */}
          <div className="absolute inset-0 bg-[linear-gradient(to_right,#80808012_1px,transparent_1px),linear-gradient(to_bottom,#80808012_1px,transparent_1px)] bg-[size:24px_24px]"></div>
          
          <div className="relative z-10">
            <h2 className="text-xl font-semibold text-white mb-6 flex items-center gap-2">
              <Cpu className="w-5 h-5 text-emerald-400" />
              Initialize Analysis
            </h2>
            
            <form onSubmit={handleAnalyze} className="space-y-6">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">Coverage Category</label>
                <select 
                  value={insuranceType} 
                  onChange={(e) => setInsuranceType(e.target.value)}
                  className="w-full rounded-xl border border-slate-600 px-4 py-3 bg-slate-900/80 text-white focus:bg-slate-900 focus:ring-2 focus:ring-emerald-500 focus:border-transparent outline-none transition-all"
                >
                  <option value="health">Health Insurance</option>
                  <option value="dental">Dental Insurance</option>
                  <option value="home">Property & Casualty</option>
                  <option value="auto">Auto & Motor</option>
                </select>
              </div>

              {/* Policy Upload Dropzone */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-emerald-500" />
                  Policy Contract (PDF / Image)
                </label>
                <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-slate-600 border-dashed rounded-xl cursor-pointer bg-slate-900/50 hover:bg-slate-800/80 hover:border-emerald-500/50 transition-all group">
                  <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    <UploadCloud className="w-6 h-6 text-slate-500 group-hover:text-emerald-400 mb-2 transition-colors" />
                    <p className="mb-1 text-xs text-slate-400"><span className="font-semibold text-emerald-400">Click to upload</span> target policy</p>
                  </div>
                  <input 
                    type="file" 
                    accept=".pdf,image/*"
                    onChange={(e) => setContractFile(e.target.files?.[0] || null)}
                    className="hidden"
                    required
                  />
                </label>
                {contractFile && (
                  <div className="mt-3 flex items-center gap-2 text-sm text-emerald-400 bg-emerald-400/10 px-3 py-2 rounded-lg border border-emerald-400/20">
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                    <span className="truncate">{contractFile.name}</span>
                  </div>
                )}
              </div>

              {/* Bills Upload Dropzone */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2 flex items-center gap-2">
                  <ImageIcon className="w-4 h-4 text-emerald-500" />
                  Ledger / Invoice / Bills (Images / PDFs)
                </label>
                <label className="flex flex-col items-center justify-center w-full h-28 border-2 border-slate-600 border-dashed rounded-xl cursor-pointer bg-slate-900/50 hover:bg-slate-800/80 hover:border-emerald-500/50 transition-all group">
                  <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    <UploadCloud className="w-6 h-6 text-slate-500 group-hover:text-emerald-400 mb-2 transition-colors" />
                    <p className="mb-1 text-xs text-slate-400"><span className="font-semibold text-emerald-400">Click to upload</span> multiple files</p>
                  </div>
                  <input 
                    type="file" 
                    accept="image/*,.pdf" 
                    multiple
                    onChange={(e) => setBillFiles(e.target.files)}
                    className="hidden"
                    required
                  />
                </label>
                {billFiles && billFiles.length > 0 && (
                  <div className="mt-3 flex items-center gap-2 text-sm text-emerald-400 bg-emerald-400/10 px-3 py-2 rounded-lg border border-emerald-400/20">
                    <CheckCircle2 className="w-4 h-4 shrink-0" />
                    <span>{billFiles.length} file(s) structured for analysis</span>
                  </div>
                )}
              </div>

              <button 
                type="submit" 
                disabled={isAnalyzing || !contractFile || !billFiles}
                className="w-full mt-8 bg-emerald-500 text-slate-950 font-bold py-3.5 rounded-xl hover:bg-emerald-400 transition-all disabled:opacity-50 disabled:bg-slate-700 disabled:text-slate-400 disabled:cursor-not-allowed flex justify-center items-center gap-2 shadow-[0_0_15px_rgba(16,185,129,0.2)] hover:shadow-[0_0_25px_rgba(16,185,129,0.4)]"
              >
                {isAnalyzing ? (
                  <>
                    <Activity className="w-5 h-5 animate-pulse" />
                    Processing Data Vectors...
                  </>
                ) : (
                  "Execute Audit"
                )}
              </button>
            </form>
          </div>
        </section>

        {/* Results Section */}
        <section className="bg-slate-900/80 rounded-2xl border border-slate-800 p-6 md:p-8 flex flex-col items-center justify-center min-h-[450px] shadow-inner relative">
          {!processStatus && !isAnalyzing && (
            <div className="text-center text-slate-500 max-w-sm">
              <div className="w-16 h-16 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto mb-5 border border-slate-700 shadow-inner relative">
                <Shield className="w-8 h-8 text-slate-500" strokeWidth={1.5} />
                <Landmark className="w-4 h-4 text-emerald-500/50 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" strokeWidth={2} />
              </div>
              <h3 className="text-slate-300 font-semibold mb-2">Awaiting Documents</h3>
              <p className="text-sm">Upload your legal contracts and billing ledgers to deploy the AI reconciliation engine.</p>
            </div>
          )}

          {isAnalyzing && (
            <div className="text-center">
              <div className="relative w-16 h-16 mx-auto mb-6">
                <div className="absolute inset-0 border-4 border-emerald-500/20 rounded-full"></div>
                <div className="absolute inset-0 border-4 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                <Database className="w-6 h-6 text-emerald-400 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2" />
              </div>
              <p className="text-emerald-400 font-bold tracking-widest uppercase text-sm animate-pulse">Running Neural Audit</p>
              <p className="text-slate-500 text-xs mt-2 font-mono">Cross-referencing coverage rules...</p>
            </div>
          )}

          {processStatus && !isAnalyzing && (
            <div className="w-full space-y-6 animate-in fade-in zoom-in duration-500 text-center">
              <div className="w-20 h-20 rounded-full bg-emerald-500/10 flex items-center justify-center mx-auto mb-4 border border-emerald-500/20">
                <CheckCircle2 className="w-10 h-10 text-emerald-400" />
              </div>
              <h2 className="text-xl font-bold text-slate-200">Processing Initiated</h2>
              <p className="text-slate-400 text-sm max-w-md mx-auto">
                Documents have been securely structured and serialized. The vector database is primed.
              </p>
              
              <div className="mt-8 p-6 bg-slate-800/40 rounded-xl border border-dashed border-slate-600 inline-block">
                <p className="text-emerald-400 font-mono text-sm">
                  {processStatus}
                </p>
                <p className="text-slate-500 text-xs mt-2">
                  (Ready to connect backend endpoints for visual data rendering)
                </p>
              </div>
            </div>
          )}
        </section>
      </main>

      {/* Floating DB Button */}
      <button 
        onClick={() => setIsModalOpen(true)}
        title="View Dataset Knowledge Base"
        className="fixed bottom-8 right-8 bg-slate-800 hover:bg-slate-700 text-slate-200 p-4 rounded-2xl shadow-2xl border border-slate-600 hover:border-emerald-500/50 transition-all group z-40 flex items-center justify-center cursor-pointer"
      >
        <Library className="w-6 h-6 text-emerald-400 group-hover:scale-110 transition-transform" />
      </button>

      {/* Dataset Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 md:p-6">
          <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm transition-opacity" onClick={() => setIsModalOpen(false)}></div>
          
          <div className="relative z-10 w-[95vw] max-w-7xl h-[90vh] bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-900/80">
              <div className="flex items-center gap-4">
                {viewingFile ? (
                  <button 
                    onClick={() => setViewingFile(null)}
                    className="p-2 -ml-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 hover:text-white transition-all flex items-center"
                  >
                    <ChevronLeft className="w-5 h-5 mr-1" /> Back
                  </button>
                ) : (
                  <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20">
                    <Database className="w-6 h-6 text-emerald-400" />
                  </div>
                )}
                <div>
                  <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2">
                    {viewingFile ? <span className="truncate max-w-sm">{viewingFile.name}</span> : 'Dataset Reference Library'}
                  </h3>
                  <p className="text-sm text-slate-400">
                    {viewingFile ? 'Document Viewer Preview' : 'Underlying data used for AI coverage recommendations'}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {viewingFile && (
                  <a 
                    href={viewingFile.url}
                    target="_blank"
                    className="text-emerald-400 hover:text-white p-2.5 rounded-xl hover:bg-emerald-500/20 transition-colors flex items-center border border-transparent mr-2"
                    title="Open in new tab"
                  >
                    <ExternalLink className="w-4 h-4 mr-2" />
                    <span className="text-xs font-bold uppercase tracking-wider">Expand</span>
                  </a>
                )}
                <button 
                  onClick={() => {
                    setIsModalOpen(false);
                    setViewingFile(null);
                  }}
                  className="text-slate-400 border border-slate-700 hover:text-white p-2.5 rounded-xl hover:bg-rose-500/20 hover:border-rose-500/50 hover:text-rose-400 transition-all bg-slate-800 shadow-xl"
                  title="Close Library"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Body */}
            <div className="flex flex-1 overflow-hidden min-h-[550px]">
              {viewingFile ? (
                /* PDF/File Viewer Screen */
                <div className="w-full h-full bg-slate-950 p-2">
                  <iframe 
                    src={viewingFile.url} 
                    className="w-full h-full rounded-xl border border-slate-700 bg-white"
                    title="Dataset Document Viewer"
                  />
                </div>
              ) : (
                /* Standard List View */
                <>
                  {/* Sidebar */}
                  <div className="w-48 bg-slate-950/50 border-r border-slate-800 p-4 flex flex-col gap-2 overflow-y-auto">
                    {(['All', 'Health', 'Auto', 'Homeowners', 'Life & Other', 'CSV'] as const).map((cat) => (
                      <button
                        key={cat}
                        onClick={() => setDatasetCategory(cat)}
                        className={`w-full text-left px-4 py-3 rounded-xl text-sm transition-all flex items-center justify-between ${
                          datasetCategory === cat 
                            ? 'bg-emerald-500/15 text-emerald-400 font-semibold border border-emerald-500/30 shadow-inner' 
                            : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200 border border-transparent'
                        }`}
                      >
                        {cat}
                        {datasetCategory === cat && <div className="w-1.5 h-1.5 rounded-full bg-emerald-400"></div>}
                      </button>
                    ))}
                  </div>

                  {/* List Area */}
                  <div className="flex-1 p-5 overflow-y-auto bg-slate-900/50">
                    <div className="space-y-3">
                      {Object.keys(datasetReferences).length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full text-slate-500 pt-12">
                          <Activity className="w-8 h-8 animate-spin text-emerald-500/50 mb-4" />
                          <p>Mapping Datasets...</p>
                        </div>
                      ) : getFilteredDatasets().length === 0 ? (
                        <div className="flex flex-col items-center justify-center h-full text-slate-500 pt-12">
                          <FileCode className="w-12 h-12 text-slate-700 mb-4" strokeWidth={1} />
                          <p>No datasets found in this category.</p>
                        </div>
                      ) : (
                        getFilteredDatasets().map((item, idx) => (
                          <div 
                            key={idx} 
                            onClick={() => setViewingFile({
                              name: item.name,
                              url: `/api/documents?file=${encodeURIComponent(item.path)}`
                            })}
                            className="group flex items-center justify-between p-4 rounded-xl border border-slate-700/50 bg-slate-800/40 hover:bg-slate-800 hover:border-emerald-500/40 hover:shadow-[0_0_15px_rgba(16,185,129,0.1)] transition-all cursor-pointer"
                          >
                            <div className="flex items-center gap-4 w-full">
                              <div className={`p-3 rounded-xl flex items-center justify-center shadow-inner ${item.type === 'pdf' ? 'bg-rose-500/10 border border-rose-500/20' : 'bg-blue-500/10 border border-blue-500/20'}`}>
                                {item.type === 'pdf' ? (
                                  <FileText className="w-6 h-6 text-rose-400" strokeWidth={1.5} />
                                ) : (
                                  <FileCode className="w-6 h-6 text-blue-400" strokeWidth={1.5} />
                                )}
                              </div>
                              <div className="flex-1 overflow-hidden">
                                <p className="text-sm font-semibold text-slate-200 truncate pr-4 group-hover:text-emerald-400 transition-colors">{item.name}</p>
                                <p className="text-xs text-slate-500 uppercase tracking-widest mt-1.5 font-mono flex items-center gap-2">
                                  <span className={item.type === 'pdf' ? 'text-rose-400/80' : 'text-blue-400/80'}>{item.type}</span> 
                                  <span className="text-slate-600">•</span>
                                  <span className="text-slate-400">{item.size}</span>
                                </p>
                              </div>
                            </div>
                            <div className="opacity-0 group-hover:opacity-100 p-2 text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-lg transition-all" title="View Document">
                              <ExternalLink className="w-5 h-5" />
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}