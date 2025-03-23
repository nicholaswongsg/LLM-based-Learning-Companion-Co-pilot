import streamlit as st
from streamlit_autorefresh import st_autorefresh

from API.escalation import escalation_handler

def InstructorUI():
    # Auto-refresh every 5 seconds
    st_autorefresh(interval=5_000, limit=None, key="instructor_refresh")

    st.subheader("Instructor Panel: Escalated Tickets")

    tickets = escalation_handler.get_instructor_tickets(st.session_state["email"])
    unresolved_tickets = [ticket for ticket in tickets if ticket[3] != "resolved"]

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Refresh"):
            st.rerun()

    with col2:
        if st.button("Logout"):
            st.session_state["logged_in"] = False
            st.session_state["email"] = None
            st.rerun()

    if not unresolved_tickets:
        st.info("No unresolved tickets assigned to you.")
    else:
        st.write("### All Unresolved Tickets")
        ticket_data = {
            "Ticket ID": [t[0] for t in unresolved_tickets],
            "Student Email": [t[1] for t in unresolved_tickets],
            "Initial Message": [t[2] for t in unresolved_tickets],
            "Status": [t[3] for t in unresolved_tickets],
            "Created At": [t[4].strftime("%Y-%m-%d %H:%M:%S") for t in unresolved_tickets],
        }
        st.dataframe(ticket_data)

        st.divider()
        st.write("### Ticket Details")
        selected_ticket_id = st.selectbox(
            "Select Ticket ID to View",
            ticket_data["Ticket ID"],
        )

        selected_ticket = next(
            ticket for ticket in unresolved_tickets if ticket[0] == selected_ticket_id
        )

        st.write(f"**Ticket ID:** {selected_ticket[0]}")
        st.write(f"**Student Email:** {selected_ticket[1]}")
        st.write(f"**Initial Message:** {selected_ticket[2]}")
        st.write(f"**Status:** {selected_ticket[3]}")
        st.write(f"**Created At:** {selected_ticket[4].strftime('%Y-%m-%d %H:%M:%S')}")

        # Conversation thread
        st.divider()
        st.subheader("Conversation Thread")
        ticket_thread = escalation_handler.get_ticket_thread(selected_ticket[0])

        if ticket_thread:
            for message in ticket_thread:
                role = "You" if message[0] == "Instructor" else "Student"
                with st.chat_message(role):
                    st.markdown(message[1])
        else:
            st.write("No follow-up messages yet.")

        # Reply to the ticket
        if follow_up_message := st.chat_input("Type your reply here..."):
            if follow_up_message.strip():
                try:
                    escalation_handler.add_ticket_message(
                        ticket_id=selected_ticket[0],
                        role="Instructor",
                        message_content=follow_up_message.strip(),
                    )
                    st.success("Reply sent successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to send reply: {e}")
            else:
                st.warning("Message cannot be empty.")

        # Update ticket status
        st.divider()
        st.subheader("Update Ticket Status")
        new_status = st.selectbox("Select New Status", ["open", "pending", "resolved"], index=0)
        if st.button("Update Status"):
            try:
                escalation_handler.update_ticket(
                    status=new_status,
                    ticket_id_to_update=selected_ticket[0],
                    email=st.session_state["email"],
                )
                st.success("Ticket status updated successfully.")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to update ticket status: {e}")
