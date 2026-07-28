import { useState, useRef, useEffect } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { Menu, LogOut, Settings, User } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useMailbox } from '../context/MailboxContext';

export const Sidebar = ({ isOpen, toggleSidebar }) => {
  const { user, logout } = useAuth();
  const { isConnected, activeMailbox } = useMailbox();
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const operationsNavItems = [
    { name: 'Dashboard', path: '/', icon: 'dashboard', roles: ['Admin', 'Editor', 'Viewer'] },
    { name: 'Workflows', path: '/workflows', icon: 'account_tree', roles: ['Admin', 'Editor', 'Viewer'] },
    { name: 'Approvals', path: '/approvals', icon: 'verified_user', roles: ['Admin', 'Editor', 'Viewer'] },
    { name: 'Email Monitoring', path: '/monitoring', icon: 'mail', roles: ['Admin', 'Editor', 'Viewer'] },
    { name: 'Automation', path: '/automation', icon: 'settings_suggest', roles: ['Admin', 'Editor', 'Viewer'] },
  ];

  const adminNavItems = [
    { name: 'Users', path: '/users', icon: 'group', roles: ['Admin'] },
    { name: 'Roles', path: '/roles', icon: 'admin_panel_settings', roles: ['Admin'] },
    { name: 'Templates', path: '/templates', icon: 'description', roles: ['Admin', 'Editor'] },
    { name: 'Logs', path: '/logs', icon: 'list_alt', roles: ['Admin'] },
    { name: 'Settings', path: '/settings', icon: 'settings', roles: ['Admin'] },
    { name: 'System Monitoring', path: '/system-monitoring', icon: 'monitor_heart', roles: ['Admin'] },
  ];

  const canSee = (item) => {
    if (!user || !user.role) return false;
    return item.roles.includes(user.role);
  };

  const renderNavItems = (items) => (
    items.filter(canSee).map((item) => (
      <NavLink
        key={item.path}
        to={item.path}
        className={({ isActive }) => 
          `flex items-center px-4 py-3 transition-colors active:opacity-80 ${
            isActive 
              ? 'text-on-primary font-label-bold border-l-2 border-primary bg-secondary-container/10' 
              : 'text-surface-variant font-label-md hover:bg-surface-container-highest hover:text-on-surface border-l-2 border-transparent'
          }`
        }
        onClick={() => {
          if (window.innerWidth < 768) toggleSidebar();
        }}
      >
        <span className="material-symbols-outlined mr-3 text-[20px]">{item.icon}</span>
        <span>{item.name}</span>
      </NavLink>
    ))
  );

  return (
    <>
      {/* Mobile overlay */}
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={toggleSidebar}
        />
      )}
      
      <aside className={`fixed left-0 top-0 h-full w-[260px] bg-inverse-surface flex flex-col overflow-y-auto border-r border-outline-variant z-50 transition-transform duration-300 ${isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'}`}>
        <div className="px-6 py-8">
          <div className="mb-8">
            <div className="flex items-baseline font-display-lg text-[32px] font-bold tracking-tight">
              <span className="text-[#2563EB]">UT</span>
              <span className="text-white">SERVIO</span>
            </div>
            <span className="text-[12px] text-surface-variant tracking-wide block mt-1">AI Email Automation</span>
            <div className="mt-3 flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-amber-500'}`}></span>
              <span className="text-[11px] font-medium text-surface-variant">
                {isConnected ? 'Gmail Synced' : 'Gmail Disconnected'}
              </span>
            </div>
          </div>
          <nav className="space-y-1">
            <div className="px-4 py-2 text-xs font-bold text-surface-variant uppercase tracking-wider">Operations</div>
            {renderNavItems(operationsNavItems)}
            
            {adminNavItems.filter(canSee).length > 0 && (
              <>
                <div className="px-4 py-2 mt-4 text-xs font-bold text-surface-variant uppercase tracking-wider">Administration</div>
                {renderNavItems(adminNavItems)}
              </>
            )}
          </nav>
        </div>
        
        <div className="mt-auto border-t border-white/10 relative" ref={dropdownRef}>
          {dropdownOpen && (
            <div className="absolute bottom-full left-4 right-4 mb-2 bg-[#2a2a2a] border border-[#3a3a3a] rounded-xl shadow-2xl overflow-hidden z-[60] transform origin-bottom">
              <div className="p-4 border-b border-[#3a3a3a] bg-[#222]">
                <p className="text-white font-label-bold text-sm truncate">{user?.name || 'User'}</p>
                <p className="text-gray-400 text-xs truncate">{user?.email || ''}</p>
              </div>
              <div className="py-1">
                <button disabled className="w-full px-4 py-2 text-left text-sm text-gray-200 hover:bg-white/10 flex items-center gap-2 transition-colors opacity-50 cursor-not-allowed">
                  <User size={16} /> My Profile
                  <span className="ml-auto text-[10px] text-gray-500">Soon</span>
                </button>
                <button disabled className="w-full px-4 py-2 text-left text-sm text-gray-200 hover:bg-white/10 flex items-center gap-2 transition-colors opacity-50 cursor-not-allowed">
                  <Settings size={16} /> Account Settings
                  <span className="ml-auto text-[10px] text-gray-500">Soon</span>
                </button>
              </div>
              <div className="py-1 border-t border-[#3a3a3a]">
                <button onClick={handleLogout} className="w-full px-4 py-2 text-left text-sm text-red-400 hover:bg-red-500/20 flex items-center gap-2 transition-colors">
                  <LogOut size={16} /> Logout
                </button>
              </div>
            </div>
          )}
          
          <div 
            className="px-6 py-6 cursor-pointer hover:bg-white/5 transition-colors flex items-center gap-3"
            onClick={() => setDropdownOpen(!dropdownOpen)}
          >
            <div className="w-10 h-10 bg-primary-container rounded-full flex items-center justify-center text-on-primary font-bold">
              {user?.name ? user.name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="text-white font-label-bold text-label-md truncate">{user?.name || 'Loading...'}</p>
              <p className="text-surface-variant text-[11px] truncate">{user?.role || 'User'}</p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
};

