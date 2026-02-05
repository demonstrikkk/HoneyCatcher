import React from 'react';
import { motion } from 'framer-motion';
import { cn } from '../utils.js';

const GlassCard = ({ children, className, delay = 0 }) => {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay, ease: "easeOut" }}
            className={cn(
                "glass-card p-6 border border-white/10 bg-surface/40 backdrop-blur-lg rounded-xl shadow-xl",
                className
            )}
        >
            {children}
        </motion.div>
    );
};

export default GlassCard;
