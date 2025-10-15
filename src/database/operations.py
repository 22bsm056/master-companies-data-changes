"""Database operations for company data management."""
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Tuple
from sqlalchemy import and_, or_, desc, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from config.database import db_config
from .models import Company, Snapshot, ChangeLog
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class DatabaseOperations:
    """Database operations handler with comprehensive error handling."""
    
    @staticmethod
    def save_companies_bulk(companies_data: List[Dict]) -> Tuple[bool, int, int]:
        """
        Save companies in bulk.
        
        Args:
            companies_data: List of company dictionaries
        
        Returns:
            Tuple of (success status, inserted count, updated count)
        """
        if not companies_data:
            logger.warning("No company data to save")
            return True, 0, 0
        
        session = db_config.get_session()
        inserted = 0
        updated = 0
        
        try:
            for data in companies_data:
                cin = data.get('cin')
                if not cin:
                    logger.warning("Skipping company without CIN")
                    continue
                
                # Check if company exists
                existing = session.query(Company).filter_by(cin=cin).first()
                
                if existing:
                    # Update existing record
                    for key, value in data.items():
                        if hasattr(existing, key):
                            setattr(existing, key, value)
                    updated += 1
                else:
                    # Insert new record
                    try:
                        company = Company(**data)
                        session.add(company)
                        inserted += 1
                    except Exception as e:
                        logger.error(f"Error creating company object for CIN {cin}: {e}")
                        continue
            
            session.commit()
            logger.info(f"[OK] Saved companies - Inserted: {inserted}, Updated: {updated}")
            return True, inserted, updated
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"[ERROR] Error saving companies: {e}")
            return False, 0, 0
        except Exception as e:
            session.rollback()
            logger.error(f"[ERROR] Unexpected error saving companies: {e}")
            return False, 0, 0
        finally:
            session.close()
    
    @staticmethod
    def create_snapshot(
        snapshot_date: date, 
        file_path: str, 
        total_records: int,
        status: str = 'SUCCESS'
    ) -> Optional[int]:
        """
        Create snapshot record.
        
        Args:
            snapshot_date: Date of snapshot
            file_path: Path to snapshot file
            total_records: Total records in snapshot
            status: Status of snapshot (SUCCESS, FAILED, IN_PROGRESS)
        
        Returns:
            Snapshot ID or None
        """
        session = db_config.get_session()
        
        try:
            # Check if snapshot for this date already exists
            existing = session.query(Snapshot).filter_by(snapshot_date=snapshot_date).first()
            
            if existing:
                # Update existing snapshot
                existing.file_path = str(file_path)
                existing.total_records = total_records
                existing.status = status
                existing.completed_at = datetime.now()
                session.commit()
                logger.info(f"[OK] Updated snapshot record for {snapshot_date}")
                return existing.id
            else:
                # Create new snapshot
                snapshot = Snapshot(
                    snapshot_date=snapshot_date,
                    file_path=str(file_path),
                    total_records=total_records,
                    status=status,
                    completed_at=datetime.now() if status == 'SUCCESS' else None
                )
                session.add(snapshot)
                session.commit()
                logger.info(f"[OK] Created snapshot record for {snapshot_date}")
                return snapshot.id
                
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"[ERROR] Error creating snapshot: {e}")
            return None
        except Exception as e:
            session.rollback()
            logger.error(f"[ERROR] Unexpected error creating snapshot: {e}")
            return None
        finally:
            session.close()
    
    @staticmethod
    def save_changes(changes: List[Dict]) -> Tuple[bool, int]:
        """
        Save change logs.
        
        Args:
            changes: List of change dictionaries
        
        Returns:
            Tuple of (success status, saved count)
        """
        if not changes:
            logger.warning("No changes to save")
            return True, 0
        
        session = db_config.get_session()
        saved_count = 0
        
        try:
            for change in changes:
                try:
                    log = ChangeLog(**change)
                    session.add(log)
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Error creating change log: {e}")
                    continue
            
            session.commit()
            logger.info(f"[OK] Saved {saved_count} change logs")
            return True, saved_count
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"[ERROR] Error saving changes: {e}")
            return False, 0
        except Exception as e:
            session.rollback()
            logger.error(f"[ERROR] Unexpected error saving changes: {e}")
            return False, 0
        finally:
            session.close()
    
    @staticmethod
    def get_company_by_cin(cin: str) -> Optional[Dict]:
        """
        Get company by CIN.
        
        Args:
            cin: Company CIN
        
        Returns:
            Company data dictionary or None
        """
        if not cin:
            logger.warning("CIN is required")
            return None
        
        session = db_config.get_session()
        
        try:
            company = session.query(Company).filter_by(cin=cin).first()
            
            if company:
                return company.to_dict()
            else:
                logger.info(f"Company with CIN {cin} not found")
                return None
                
        except SQLAlchemyError as e:
            logger.error(f"[ERROR] Error retrieving company by CIN: {e}")
            return None
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error retrieving company: {e}")
            return None
        finally:
            session.close()
    
    @staticmethod
    def search_companies(query: str, limit: int = 10) -> List[Dict]:
        """
        Search companies by name or CIN.
        
        Args:
            query: Search query
            limit: Maximum results
        
        Returns:
            List of company dictionaries
        """
        if not query:
            logger.warning("Search query is required")
            return []
        
        session = db_config.get_session()
        
        try:
            companies = session.query(Company).filter(
                or_(
                    Company.company_name.ilike(f"%{query}%"),
                    Company.cin.ilike(f"%{query}%")
                )
            ).limit(limit).all()
            
            results = [c.to_dict() for c in companies]
            logger.info(f"[OK] Found {len(results)} companies for query: '{query}'")
            return results
            
        except SQLAlchemyError as e:
            logger.error(f"[ERROR] Error searching companies: {e}")
            return []
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error searching companies: {e}")
            return []
        finally:
            session.close()
    
    @staticmethod
    def get_changes_by_date_range(
        start_date: date, 
        end_date: date
    ) -> List[Dict]:
        """
        Get changes within date range.
        
        Args:
            start_date: Start date
            end_date: End date
        
        Returns:
            List of change dictionaries
        """
        session = db_config.get_session()
        
        try:
            changes = session.query(ChangeLog).filter(
                and_(
                    ChangeLog.change_date >= start_date,
                    ChangeLog.change_date <= end_date
                )
            ).order_by(desc(ChangeLog.change_date)).all()
            
            results = [c.to_dict() for c in changes]
            logger.info(f"[OK] Found {len(results)} changes between {start_date} and {end_date}")
            return results
            
        except SQLAlchemyError as e:
            logger.error(f"[ERROR] Error retrieving changes by date range: {e}")
            return []
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error retrieving changes: {e}")
            return []
        finally:
            session.close()
    
    @staticmethod
    def get_changes_by_cin(cin: str) -> List[Dict]:
        """
        Get all changes for a company.
        
        Args:
            cin: Company CIN
        
        Returns:
            List of change dictionaries
        """
        if not cin:
            logger.warning("CIN is required")
            return []
        
        session = db_config.get_session()
        
        try:
            changes = session.query(ChangeLog).filter_by(cin=cin)\
                .order_by(desc(ChangeLog.change_date)).all()
            
            results = [c.to_dict() for c in changes]
            logger.info(f"[OK] Found {len(results)} changes for CIN: {cin}")
            return results
            
        except SQLAlchemyError as e:
            logger.error(f"[ERROR] Error retrieving changes by CIN: {e}")
            return []
        except Exception as e:
            logger.error(f"[ERROR] Unexpected error retrieving changes: {e}")
            return []
        finally:
            session.close()
    
    @staticmethod
    def get_statistics(days: int = 30) -> Dict[str, Any]:
        """
        Get statistics for dashboard.
        
        Args:
            days: Number of days to analyze
        
        Returns:
            Statistics dictionary
        """
        session = db_config.get_session()
        
        try:
            start_date = datetime.now().date() - timedelta(days=days)
            
            # Total companies
            try:
                total_companies = session.query(Company).count()
            except Exception as e:
                logger.warning(f"Could not get total companies: {e}")
                total_companies = 0
            
            # Active companies
            try:
                active_companies = session.query(Company).filter_by(
                    company_status='Active'
                ).count()
            except Exception as e:
                logger.warning(f"Could not get active companies: {e}")
                active_companies = 0
            
            # Changes in period
            try:
                total_changes = session.query(ChangeLog).filter(
                    ChangeLog.change_date >= start_date
                ).count()
            except Exception as e:
                logger.warning(f"Could not get total changes: {e}")
                total_changes = 0
            
            # Changes by type
            changes_by_type = {
                'NEW': 0,
                'MODIFIED': 0,
                'DELETED': 0
            }
            
            try:
                for change_type in ['NEW', 'MODIFIED', 'DELETED']:
                    count = session.query(ChangeLog).filter(
                        and_(
                            ChangeLog.change_type == change_type,
                            ChangeLog.change_date >= start_date
                        )
                    ).count()
                    changes_by_type[change_type] = count
            except Exception as e:
                logger.warning(f"Could not get changes by type: {e}")
            
            stats = {
                'total_companies': total_companies,
                'active_companies': active_companies,
                'total_changes': total_changes,
                'changes_by_type': changes_by_type
            }
            
            logger.info(f"[OK] Retrieved statistics: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"[ERROR] Error getting statistics: {e}")
            # Return default values on error
            return {
                'total_companies': 0,
                'active_companies': 0,
                'total_changes': 0,
                'changes_by_type': {
                    'NEW': 0,
                    'MODIFIED': 0,
                    'DELETED': 0
                }
            }
        finally:
            session.close()
    
    @staticmethod
    def get_all_snapshots(limit: int = 10) -> List[Dict]:
        """
        Get all snapshots ordered by date.
        
        Args:
            limit: Maximum snapshots to return
        
        Returns:
            List of snapshot dictionaries
        """
        session = db_config.get_session()
        
        try:
            snapshots = session.query(Snapshot)\
                .order_by(desc(Snapshot.snapshot_date))\
                .limit(limit).all()
            
            results = []
            for snapshot in snapshots:
                results.append({
                    'id': snapshot.id,
                    'snapshot_date': str(snapshot.snapshot_date),
                    'file_path': snapshot.file_path,
                    'total_records': snapshot.total_records,
                    'status': snapshot.status,
                    'created_at': str(snapshot.created_at),
                    'completed_at': str(snapshot.completed_at) if snapshot.completed_at else None
                })
            
            return results
            
        except SQLAlchemyError as e:
            logger.error(f"[ERROR] Error retrieving snapshots: {e}")
            return []
        finally:
            session.close()
    
    @staticmethod
    def get_latest_snapshot() -> Optional[Dict]:
        """
        Get the most recent snapshot.
        
        Returns:
            Snapshot dictionary or None
        """
        session = db_config.get_session()
        
        try:
            snapshot = session.query(Snapshot)\
                .order_by(desc(Snapshot.snapshot_date))\
                .first()
            
            if snapshot:
                return {
                    'id': snapshot.id,
                    'snapshot_date': str(snapshot.snapshot_date),
                    'file_path': snapshot.file_path,
                    'total_records': snapshot.total_records,
                    'status': snapshot.status,
                    'created_at': str(snapshot.created_at),
                    'completed_at': str(snapshot.completed_at) if snapshot.completed_at else None
                }
            return None
            
        except SQLAlchemyError as e:
            logger.error(f"[ERROR] Error retrieving latest snapshot: {e}")
            return None
        finally:
            session.close()
    
    @staticmethod
    def delete_old_snapshots(keep_days: int = 30) -> int:
        """
        Delete snapshots older than specified days.
        
        Args:
            keep_days: Number of days to keep
        
        Returns:
            Number of deleted snapshots
        """
        session = db_config.get_session()
        
        try:
            cutoff_date = datetime.now().date() - timedelta(days=keep_days)
            
            deleted_count = session.query(Snapshot).filter(
                Snapshot.snapshot_date < cutoff_date
            ).delete()
            
            session.commit()
            logger.info(f"[OK] Deleted {deleted_count} old snapshots")
            return deleted_count
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"[ERROR] Error deleting old snapshots: {e}")
            return 0
        finally:
            session.close()
    
    @staticmethod
    def get_companies_by_status(status: str, limit: int = 100) -> List[Dict]:
        """
        Get companies by status.
        
        Args:
            status: Company status (e.g., 'Active', 'Strike Off')
            limit: Maximum results
        
        Returns:
            List of company dictionaries
        """
        session = db_config.get_session()
        
        try:
            companies = session.query(Company)\
                .filter_by(company_status=status)\
                .limit(limit).all()
            
            return [c.to_dict() for c in companies]
            
        except SQLAlchemyError as e:
            logger.error(f"[ERROR] Error retrieving companies by status: {e}")
            return []
        finally:
            session.close()
    
    @staticmethod
    def get_companies_by_category(category: str, limit: int = 100) -> List[Dict]:
        """
        Get companies by category.
        
        Args:
            category: Company category
            limit: Maximum results
        
        Returns:
            List of company dictionaries
        """
        session = db_config.get_session()
        
        try:
            companies = session.query(Company)\
                .filter_by(company_category=category)\
                .limit(limit).all()
            
            return [c.to_dict() for c in companies]
            
        except SQLAlchemyError as e:
            logger.error(f"[ERROR] Error retrieving companies by category: {e}")
            return []
        finally:
            session.close()
    
    @staticmethod
    def get_recent_changes(limit: int = 50) -> List[Dict]:
        """
        Get most recent changes.
        
        Args:
            limit: Maximum results
        
        Returns:
            List of change dictionaries
        """
        session = db_config.get_session()
        
        try:
            changes = session.query(ChangeLog)\
                .order_by(desc(ChangeLog.created_at))\
                .limit(limit).all()
            
            return [c.to_dict() for c in changes]
            
        except SQLAlchemyError as e:
            logger.error(f"[ERROR] Error retrieving recent changes: {e}")
            return []
        finally:
            session.close()
    
    @staticmethod
    def count_companies_by_state() -> Dict[str, int]:
        """
        Count companies by state.
        
        Returns:
            Dictionary of {state: count}
        """
        session = db_config.get_session()
        
        try:
            results = session.query(
                Company.company_state_code,
                func.count(Company.id).label('count')
            ).group_by(Company.company_state_code).all()
            
            return {state: count for state, count in results if state}
            
        except SQLAlchemyError as e:
            logger.error(f"[ERROR] Error counting companies by state: {e}")
            return {}
        finally:
            session.close()
    
    @staticmethod
    def count_companies_by_status() -> Dict[str, int]:
        """
        Count companies by status.
        
        Returns:
            Dictionary of {status: count}
        """
        session = db_config.get_session()
        
        try:
            results = session.query(
                Company.company_status,
                func.count(Company.id).label('count')
            ).group_by(Company.company_status).all()
            
            return {status: count for status, count in results if status}
            
        except SQLAlchemyError as e:
            logger.error(f"[ERROR] Error counting companies by status: {e}")
            return {}
        finally:
            session.close()
    
    @staticmethod
    def get_database_health() -> Dict[str, Any]:
        """
        Check database health and get basic metrics.
        
        Returns:
            Health status dictionary
        """
        session = db_config.get_session()
        
        try:
            # Test connection
            session.execute("SELECT 1")
            
            # Get counts
            company_count = session.query(Company).count()
            snapshot_count = session.query(Snapshot).count()
            change_count = session.query(ChangeLog).count()
            
            return {
                'status': 'healthy',
                'connected': True,
                'companies_count': company_count,
                'snapshots_count': snapshot_count,
                'changes_count': change_count,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"[ERROR] Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'connected': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
        finally:
            session.close()
    
    @staticmethod
    def bulk_delete_companies(cins: List[str]) -> Tuple[bool, int]:
        """
        Delete multiple companies by CIN.
        
        Args:
            cins: List of company CINs
        
        Returns:
            Tuple of (success status, deleted count)
        """
        session = db_config.get_session()
        
        try:
            deleted = session.query(Company).filter(
                Company.cin.in_(cins)
            ).delete(synchronize_session=False)
            
            session.commit()
            logger.info(f"[OK] Deleted {deleted} companies")
            return True, deleted
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"[ERROR] Error deleting companies: {e}")
            return False, 0
        finally:
            session.close()