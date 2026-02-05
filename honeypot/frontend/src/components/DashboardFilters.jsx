import React from 'react';
import { Filter, Search, Globe, Shield, Activity, Volume2 } from 'lucide-react';

const DashboardFilters = ({ onFilterChange }) => {
    const [filters, setFilters] = React.useState({
        voiceEnabled: null,
        language: '',
        minScamScore: 0,
        voiceMode: ''
    });

    const handleChange = (key, value) => {
        const newFilters = { ...filters, [key]: value };
        setFilters(newFilters);
        if (onFilterChange) onFilterChange(newFilters);
    };

    return (
        <div className="flex flex-wrap items-center gap-4 p-4 bg-slate-900/40 backdrop-blur-xl border border-white/5 rounded-2xl">
            <div className="flex items-center gap-2 px-3 py-1.5 bg-indigo-500/10 border border-indigo-500/20 rounded-xl text-indigo-400">
                <Filter className="w-4 h-4" />
                <span className="text-xs font-bold uppercase tracking-wider">Filters</span>
            </div>

            {/* Voice Toggle */}
            <div className="flex items-center gap-2">
                <label className="text-xs text-slate-500 font-medium">I/O Type:</label>
                <select
                    className="bg-slate-800 border-none rounded-lg text-xs text-slate-300 py-1.5 focus:ring-1 focus:ring-indigo-500"
                    onChange={(e) => handleChange('voiceEnabled', e.target.value === 'all' ? null : e.target.value === 'voice')}
                >
                    <option value="all">All Channels</option>
                    <option value="voice">Voice Only</option>
                    <option value="text">Text Only</option>
                </select>
            </div>

            {/* Language Filter */}
            <div className="flex items-center gap-2">
                <Globe className="w-3.5 h-3.5 text-slate-500" />
                <select
                    className="bg-slate-800 border-none rounded-lg text-xs text-slate-300 py-1.5 focus:ring-1 focus:ring-indigo-500"
                    onChange={(e) => handleChange('language', e.target.value)}
                >
                    <option value="">Any Language</option>
                    <option value="en">English</option>
                    <option value="hi">Hindi</option>
                    <option value="ta">Tamil</option>
                    <option value="te">Telugu</option>
                    <option value="ml">Malayalam</option>
                    <option value="bn">Bengali</option>
                </select>
            </div>

            {/* Scam Confidence */}
            <div className="flex items-center gap-2">
                <Shield className="w-3.5 h-3.5 text-slate-500" />
                <select
                    className="bg-slate-800 border-none rounded-lg text-xs text-slate-300 py-1.5 focus:ring-1 focus:ring-indigo-500"
                    onChange={(e) => handleChange('minScamScore', parseFloat(e.target.value))}
                >
                    <option value="0">Min Confidence: 0%</option>
                    <option value="0.5">Min Confidence: 50%+</option>
                    <option value="0.8">Min Confidence: 80%+</option>
                    <option value="0.95">Confirmed Scams (95%+)</option>
                </select>
            </div>

            {/* AI Mode */}
            <div className="flex items-center gap-2">
                <Activity className="w-3.5 h-3.5 text-slate-500" />
                <select
                    className="bg-slate-800 border-none rounded-lg text-xs text-slate-300 py-1.5 focus:ring-1 focus:ring-indigo-500"
                    onChange={(e) => handleChange('voiceMode', e.target.value)}
                >
                    <option value="">Any Auto Mode</option>
                    <option value="ai_speaks">AI Speaks</option>
                    <option value="ai_suggests">AI Suggests</option>
                </select>
            </div>

            {/* Reset Button */}
            <button
                onClick={() => {
                    const reset = { voiceEnabled: null, language: '', minScamScore: 0, voiceMode: '' };
                    setFilters(reset);
                    onFilterChange(reset);
                }}
                className="ml-auto text-xs text-indigo-400 hover:text-indigo-300 transition-colors font-medium"
            >
                Reset Filters
            </button>
        </div>
    );
};

export default DashboardFilters;
