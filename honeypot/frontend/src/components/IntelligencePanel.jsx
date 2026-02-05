import React from 'react';
import GlassCard from './GlassCard';
import { CreditCard, Globe, Phone, AlertTriangle, Fingerprint } from 'lucide-react';

const IntelligencePanel = ({ intelligence }) => {
    const categories = [
        { id: 'bank_accounts', label: 'Bank Accounts', icon: CreditCard, color: 'text-blue-400' },
        { id: 'upi_ids', label: 'UPI IDs', icon: Fingerprint, color: 'text-orange-400' },
        { id: 'phone_numbers', label: 'Phone Numbers', icon: Phone, color: 'text-green-400' },
        { id: 'urls', label: 'Phishing Links', icon: Globe, color: 'text-cyan-400' },
        { id: 'scam_keywords', label: 'Triggers', icon: AlertTriangle, color: 'text-yellow-400' },
    ];

    if (!intelligence) return null;

    return (
        <GlassCard className="h-full overflow-y-auto">
            <h2 className="text-lg font-bold mb-6 flex items-center gap-2">
                <span className="w-2 h-6 bg-primary rounded-full" />
                Extracted Intelligence
            </h2>

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
