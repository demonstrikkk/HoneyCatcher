import React from 'react';
import { cn } from '../utils.js';
import { Bot, User } from 'lucide-react';
import { motion } from 'framer-motion';

const MessageBubble = ({ message }) => {
    const isAgent = (message.sender || message.role) === 'agent';

    return (
        <motion.div
            initial={{ opacity: 0, x: isAgent ? -10 : 10 }}
            animate={{ opacity: 1, x: 0 }}
            className={cn(
                "flex gap-4 max-w-[80%]",
                isAgent ? "self-start" : "self-end flex-row-reverse"
            )}
        >
            <div className={cn(
                "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                isAgent ? "bg-primary/20 text-primary" : "bg-danger/20 text-danger"
            )}>
                {isAgent ? <Bot size={16} /> : <User size={16} />}
            </div>

            <div className="flex flex-col gap-1">
                <div className={cn(
                    "p-4 rounded-2xl text-sm leading-relaxed",
                    isAgent
                        ? "bg-surface border border-white/5 text-gray-200 rounded-tl-sm"
                        : "bg-surface border border-danger/20 text-gray-200 rounded-tr-sm"
                )}>
                    {message.content}
                </div>
                <span className="text-[10px] text-gray-600 px-2">
                    {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    {/* In real app, use message.timestamp */}
                </span>
            </div>
        </motion.div>
    );
};

export default MessageBubble;
