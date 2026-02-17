from typing import Dict, List, Optional, Callable, Any, Union
import time
import re
from playwright.sync_api import Page, Locator, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from browser_types import (
    BrowserCommand, InteractionResult, DistilledElement, ActionType, 
    LocatorStrategy, FailureKind
)

class BrowserInteractionAgent:
    def __init__(self, page: Page, perception_callback: Callable[[], List[DistilledElement]]):
        self.page = page
        self.perception_callback = perception_callback
        self.element_map: Dict[str, DistilledElement] = {}
        # Secure channel mock - in real app this would be injected securely
        self._secrets: Dict[str, str] = {} 

    def register_secret(self, placeholder: str, real_value: str):
        self._secrets[placeholder] = real_value

    def update_map(self, elements: List[DistilledElement]):
        """Updates the in-memory mapping of element IDs to their properties."""
        self.element_map = {el.element_id: el for el in elements}

    def _get_locators_for_distilled_element(self, element: DistilledElement) -> List[tuple[LocatorStrategy, Locator]]:
        """
        Generates a list of (Strategy, Locator) tuples in priority order.
        """
        strategies = []

        # 1. Set-of-Marks / distilled ID
        # Assuming the perception layer might add a data attribute or we know a specific ID attribute.
        # If the element has a unique 'dom_id' or 'mark_id' in its attributes.
        if element.attributes:
            for key in ['data-mark-id', 'data-element-id', 'id']:
                if key in element.attributes:
                    val = element.attributes[key]
                    strategies.append((
                        LocatorStrategy.DISTILLED_ID,
                        self.page.locator(f"[{key}='{val}']")
                    ))
                    break # Use the best ID found

        # 2. Stable attributes
        if element.attributes:
            for key in ['data-testid', 'data-test', 'data-qa']:
                if key in element.attributes:
                    val = element.attributes[key]
                    strategies.append((
                        LocatorStrategy.TEST_ID,
                        self.page.locator(f"[{key}='{val}']")
                    ))
        
        # 3. ARIA and role-based selectors
        # strict mode is implicit in playwright unless .first() is called, but we handle it.
        if element.role:
            try:
                # Prepare options
                # element.name is usually the accessible name
                name_filter = element.name if element.name else None
                # We can refine this using exact=True if we are confident
                strategies.append((
                    LocatorStrategy.ARIA_ROLE,
                    self.page.get_by_role(element.role, name=name_filter)
                ))
            except Exception:
                pass # valid role check might fail if role is obscure

            if element.tag_name == "input" or element.tag_name == "textarea":
                # Label
                # We don't have the label text directly in DistilledElement structure defined simply, 
                # but let's assume 'name' might be it or we rely on getByLabel if we have the text
                pass 
                # Placeholder
                if element.attributes and 'placeholder' in element.attributes:
                    strategies.append((
                        LocatorStrategy.ARIA_ROLE,
                        self.page.get_by_placeholder(element.attributes['placeholder'])
                    ))

        # 4. Text plus structure
        if element.text and len(element.text.strip()) > 0:
            # simple getByText
            strategies.append((
                LocatorStrategy.TEXT,
                self.page.get_by_text(element.text, exact=True) # Try exact first
            ))
            strategies.append((
                LocatorStrategy.TEXT,
                self.page.locator(element.tag_name, has_text=element.text)
            ))

        # 5. Carefully-scoped CSS
        # If we have selector hints from perception
        if element.selector_hints:
            for sel in element.selector_hints:
                # Avoid "random" looking classes if possible, but use what provided
                strategies.append((
                    LocatorStrategy.CSS,
                    self.page.locator(sel)
                ))
        
        return strategies

    def _resolve_locator_with_retries(self, element_id: str, deadline: float) -> tuple[Optional[LocatorStrategy], Optional[Locator], Optional[str]]:
        """
        Attempts to find a working locator.
        Returns (Strategy, Locator, ErrorMessage).
        Handles retries with backoff [1, 2, 4] within deadline.
        """
        backoffs = [1, 2, 4]
        attempt = 0
        
        # Track if we encountered specific failure types
        found_ambiguous = False
        last_ambiguous_selector = None

        while time.time() < deadline:
            # 1. Fetch element data
            distilled = self.element_map.get(element_id)
            if not distilled:
                # Try to refresh map once
                new_elements = self.perception_callback()
                self.update_map(new_elements)
                distilled = self.element_map.get(element_id)
                if not distilled:
                    return None, None, f"Element ID {element_id} not found in perception map."

            # 2. Get strategies
            strategies = self._get_locators_for_distilled_element(distilled)
            
            attempted_selectors_this_pass = []
            
            for strategy, loc in strategies:
                attempted_selectors_this_pass.append(str(loc))
                try:
                    # Check for attached, visible, stable
                    remaining = (deadline - time.time()) * 1000
                    if remaining <= 0: break

                    # Check for ambiguity and visibility
                    count = loc.count()
                    if count == 0:
                        continue 
                    if count > 1:
                        found_ambiguous = True
                        last_ambiguous_selector = str(loc)
                        continue 
                    
                    if loc.is_visible():
                        return strategy, loc, None
                    
                except Exception:
                    pass

            # If we fall through strategies, we failed this attempt.
            attempt += 1
            if attempt > len(backoffs):
                break
            
            sleep_time = backoffs[attempt-1]
            if time.time() + sleep_time > deadline:
                break 
            
            time.sleep(sleep_time)
            # Refresh map on retry
            new_elements = self.perception_callback()
            self.update_map(new_elements)

        if found_ambiguous:
            return None, None, f"Ambiguous locator found (matches multiple elements): {last_ambiguous_selector}"
            
        return None, None, f"Could not resolve valid locator after retries."

    def execute_command(self, command: BrowserCommand) -> InteractionResult:
        start_time = time.time()
        timeout_budget = 20.0 # seconds
        deadline = start_time + timeout_budget
        
        initial_url = self.page.url
        
        try:
            if command.action_type == ActionType.CLICK:
                if not command.element_id:
                    return InteractionResult(False, command.action_type, failure_kind=FailureKind.GENERIC_ERROR, failure_reason="Missing element_id")

                strategy, locator, error = self._resolve_locator_with_retries(command.element_id, deadline)
                
                if not locator:
                    return InteractionResult(
                        False, 
                        command.action_type, 
                        command.element_id, 
                        failure_kind=FailureKind.AMBIGUOUS_LOCATOR if "multiple" in (error or "") else FailureKind.TIMEOUT_OR_STUCK,
                        failure_reason=error,
                        url_after=self.page.url
                    )

                # Execute Click
                # Calculate remaining time for the action itself
                remaining_ms = max(0, (deadline - time.time()) * 1000)
                
                try:
                    locator.click(timeout=remaining_ms)
                    
                    # If nav triggers, wait for stabilization?
                    # "If the click triggers navigation, wait for network/URL stabilization within your remaining time budget."
                    # We can do a smart wait.
                    try:
                        self.page.wait_for_load_state("networkidle", timeout=2000) # fast wait
                    except:
                        pass # Ignore loading timeouts, we check progress later

                except PlaywrightTimeoutError:
                     return InteractionResult(
                        False, command.action_type, command.element_id, strategy, self.page.url,
                        failure_kind=FailureKind.TIMEOUT_OR_STUCK,
                        failure_reason="Click timed out"
                    )
                except Exception as e:
                     return InteractionResult(
                        False, command.action_type, command.element_id, strategy, self.page.url,
                        failure_kind=FailureKind.GENERIC_ERROR,
                        failure_reason=str(e)
                    )

                return InteractionResult(
                    True, command.action_type, command.element_id, strategy, self.page.url,
                    progress_signal="url_change" if self.page.url != initial_url else "click_success"
                )

            elif command.action_type == ActionType.TYPE:
                if not command.element_id or command.text_content is None:
                    return InteractionResult(False, command.action_type, failure_kind=FailureKind.GENERIC_ERROR, failure_reason="Missing id or text")

                strategy, locator, error = self._resolve_locator_with_retries(command.element_id, deadline)
                if not locator:
                    return InteractionResult(
                        False, command.action_type, command.element_id, 
                        failure_kind=FailureKind.TIMEOUT_OR_STUCK, 
                        failure_reason=error, 
                        url_after=self.page.url
                    )

                # Handle Secrets
                text_to_type = command.text_content
                is_secret = False
                # Check placeholders
                for key, val in self._secrets.items():
                    if key in text_to_type:
                        text_to_type = text_to_type.replace(key, val)
                        is_secret = True
                
                remaining_ms = max(0, (deadline - time.time()) * 1000)
                try:
                    locator.fill(text_to_type, timeout=remaining_ms)
                    
                    # Verification (if not secret and cheap)
                    if not is_secret:
                        # "optionally verify... if cheap"
                        pass

                except PlaywrightTimeoutError:
                     return InteractionResult(
                        False, command.action_type, command.element_id, strategy, self.page.url,
                        failure_kind=FailureKind.TIMEOUT_OR_STUCK,
                        failure_reason="Type timed out"
                    )

                return InteractionResult(
                    True, command.action_type, command.element_id, strategy, self.page.url, 
                    progress_signal="input_filled"
                )
            
            elif command.action_type == ActionType.NAVIGATE:
                if not command.url:
                    return InteractionResult(False, command.action_type, failure_kind=FailureKind.GENERIC_ERROR, failure_reason="Missing URL")
                
                try:
                    self.page.goto(command.url, timeout=timeout_budget*1000)
                except Exception as e:
                    return InteractionResult(
                        False, command.action_type, url_after=self.page.url,
                        failure_kind=FailureKind.GENERIC_ERROR, failure_reason=str(e)
                    )
                
                return InteractionResult(
                    True, command.action_type, url_after=self.page.url, progress_signal="navigation"
                )

        except Exception as e:
            return InteractionResult(
                False, command.action_type, url_after=self.page.url, 
                failure_kind=FailureKind.GENERIC_ERROR, failure_reason=f"Unexpected error: {str(e)}"
            )

        return InteractionResult(False, command.action_type, failure_kind=FailureKind.GENERIC_ERROR, failure_reason="Unknown command")
