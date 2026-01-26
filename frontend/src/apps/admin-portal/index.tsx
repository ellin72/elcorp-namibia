import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';

const AdminPortal: React.FC = () => {
    return (
        <Routes>
            <Route path="/" element={<div className="container py-5"><h1>Admin Portal - Coming Soon</h1></div>} />
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    );
};

export default AdminPortal;
