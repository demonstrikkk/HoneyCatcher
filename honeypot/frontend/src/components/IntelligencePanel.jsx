import React, { useState } from 'react';
import GlassCard from './GlassCard';
import { CreditCard, Globe, Phone, AlertTriangle, Fingerprint, TestTube, Loader } from 'lucide-react';
import api from '../services/api';

const IntelligencePanel = ({ intelligence, enableTesting = false }) => {
    const [testing, setTesting] = useState(false);
    const [testResults, setTestResults] = useState(null);
    const [testError, setTestError] = useState(null);

    const categories = [
        { id: 'bank_accounts', label: 'Bank Accounts', icon: CreditCard, color: 'text-blue-400' },
        { id: 'upi_ids', label: 'UPI IDs', icon: Fingerprint, color: 'text-orange-400' },
        { id: 'phone_numbers', label: 'Phone Numbers', icon: Phone, color: 'text-green-400' },
        { id: 'urls', label: 'Phishing Links', icon: Globe, color: 'text-cyan-400' },
        { id: 'scam_keywords', label: 'Triggers', icon: AlertTriangle, color: 'text-yellow-400' },
    ];

    const handleTestVirusTotal = async () => {
        setTesting(true);
        setTestError(null);
        setTestResults(null);

        try {
            console.log('🧪 Testing VirusTotal...');
            
            // Test with known malicious URLs
            const response = await api.post('/test-virustotal', {
                urls: [
                    'http://malware.testing.google.test/testing/malware/',
                    'https://www.google.com'
                ]
            });

            console.log('✅ VirusTotal test results:', response.data);
            setTestResults(response.data);
        } catch (error) {
            console.error('❌ VirusTotal test failed:', error);
            setTestError(error.response?.data?.detail || error.message);
        } finally {
            setTesting(false);
        }
    };

    if (!intelligence) return null;

    return (
        <GlassCard className="h-full overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold flex items-center gap-2">
                    <span className="w-2 h-6 bg-primary rounded-full" />
                    Extracted Intelligence
                </h2>
                
                {enableTesting && (
                    <button
                        onClick={handleTestVirusTotal}
                        disabled={testing}
                        className="flex items-center gap-2 px-3 py-1.5 bg-purple-500/20 hover:bg-purple-500/30 
                                 border border-purple-500/50 rounded text-xs font-semibold text-purple-300
                                 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {testing ? (
                            <>
                                <Loader size={14} className="animate-spin" />
                                Testing...
                            </>
                        ) : (
                            <>
                                <TestTube size={14} />
                                Test VirusTotal
                            </>
                        )}
                    </button>
                )}
            </div>

            {/* VirusTotal Test Results */}
            {testResults && (
                <div className="mb-6 p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                    <h3 className="text-sm font-semibold text-purple-300 mb-3 flex items-center gap-2">
                        <TestTube size={14} />
                        VirusTotal Test Results
                    </h3>
                    <div className="space-y-2">
                        {testResults.results?.map((result, idx) => (
                            <div key={idx} className="bg-black/30 p-3 rounded text-xs">
                                <div className="font-mono text-gray-400 mb-2 break-all">{result.url}</div>
                                <div className={`font-semibold ${result.is_safe ? 'text-green-400' : 'text-red-400'}`}>
                                    {result.summary}
                                </div>
                                {result.findings?.length > 0 && (
                                    <div className="mt-2 text-gray-500">
                                        {result.findings.slice(0, 3).join(', ')}
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {testError && (
                <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg">
                    <h3 className="text-sm font-semibold text-red-300 mb-2">Test Failed</h3>
                    <p className="text-xs text-red-400">{testError}</p>
                </div>
            )}

            <div className="space-y-6">
                {categories.map((cat) => {
                    const items = intelligence[cat.id] || [];
                    if (items.length === 0) return null;

                    return (
                        <div key={cat.id} className="space-y-3">
                            <div className="flex items-center gap-2 text-sm font-semibold text-gray-400 uppercase tracking-wider">
                                <cat.icon size={14} className={cat.color} />
                                {cat.label}
                            </div>
                            <div className="grid gap-2">
                                {items.map((item, i) => (
                                    <div key={i} className="bg-white/5 px-3 py-2 rounded text-sm font-mono text-gray-300 border border-white/5 break-all">
                                        {item}
                                    </div>
                                ))}
                            </div>
                        </div>
                    );
                })}

                {Object.values(intelligence).every(arr => arr.length === 0) && (
                    <div className="text-center py-10 text-gray-600 italic">
                        No intelligence extracted yet.
                    </div>
                )}
            </div>
        </GlassCard>
    );
};

export default IntelligencePanel;
