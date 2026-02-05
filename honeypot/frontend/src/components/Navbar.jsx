import React from 'react';
import { Link } from 'react-router-dom';
import { ShieldAlert, Activity } from 'lucide-react';

const Navbar = () => {
    return (
        <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-background/80 backdrop-blur-lg h-16 flex items-center px-8 justify-between">
            <Link to="/" className="flex items-center gap-3">
                <div className="bg-primary/20 p-2 rounded-lg">
                    <ShieldAlert className="w-6 h-6 text-primary" />
                </div>
                <span className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-white to-gray-400">
                    HoneyPot<span className="font-light text-primary">.AI</span>
                </span>
            </Link>

            <div className="flex items-center gap-6">
                <div className="flex items-center gap-2 text-sm text-gray-400">
                    <Activity className="w-4 h-4 text-emerald-500 animate-pulse" />
                    System Operational
                </div>
                <div className="h-8 w-px bg-white/10" />
                <Link to="/" className="text-sm font-medium hover:text-white transition-colors text-gray-400">
                    Testing Lab
                </Link>
                <Link to="/voice" className="text-sm font-medium hover:text-white transition-colors text-gray-400 flex items-center gap-1">
                    Voice Lab <span className="text-[8px] bg-indigo-500/20 text-indigo-400 px-1.5 py-0.5 rounded-full border border-indigo-500/30">NEW</span>
                </Link>
                <Link to="/dashboard" className="text-sm font-medium hover:text-white transition-colors text-gray-400">
                    Sessions
                </Link>
            </div>
        </nav>
    );
};

export default Navbar;
