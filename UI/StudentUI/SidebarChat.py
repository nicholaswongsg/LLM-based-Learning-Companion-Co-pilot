import streamlit as st
from API.escalation import escalation_handler


# Sidebar Logic
def SidebarUI():
    st.sidebar.title("Escalated Tickets")
    tickets = escalation_handler.get_student_tickets(st.session_state["email"])

    if tickets:
        # Display tickets in a selectbox
        ticket_ids = [f"Ticket #{ticket[0]}" for ticket in tickets]
        selected_ticket_label = st.sidebar.selectbox(
            "Your Escalated Tickets", ticket_ids, index=0
        )

        # Find selected ticket details
        selected_ticket = next(
            ticket for ticket in tickets if f"Ticket #{ticket[0]}" == selected_ticket_label
        )

        # Display ticket details
        st.sidebar.subheader("Ticket Details")
        st.sidebar.write(f"**Message:** {selected_ticket[2]}")
        st.sidebar.write(f"**Status:** {selected_ticket[3]}")
        st.sidebar.write(f"**Created At:** {selected_ticket[4].strftime('%Y-%m-%d %H:%M:%S')}")

        # Show conversation thread
        st.sidebar.subheader("Follow-Up Messages")
        ticket_thread = escalation_handler.get_ticket_thread(selected_ticket[0])
        if ticket_thread:
            for message in ticket_thread:
                role = "You" if message[0] == "Student" else "Instructor"
                st.sidebar.write(f"**{role}:** {message[1]}")
        else:
            st.sidebar.write("No follow-up messages yet.")

        # Disable follow-up input if the ticket is resolved
        if selected_ticket[3] == "resolved":
            st.sidebar.subheader("Send a Follow-Up")
            st.sidebar.warning("This ticket is resolved. You can no longer reply to it.")
        else:
            # Input for new follow-up message
            st.sidebar.subheader("Send a Follow-Up")
            follow_up_message = st.sidebar.text_area("Type your follow-up message here...")
            if st.sidebar.button("Send Message"):
                if follow_up_message.strip():
                    try:
                        escalation_handler.add_ticket_message(
                            ticket_id=selected_ticket[0],
                            role="Student",
                            message_content=follow_up_message.strip(),
                        )
                        st.sidebar.success("Follow-up message sent successfully!")
                        st.rerun()
                    except Exception as e:
                        st.sidebar.error(f"Error sending message: {e}")
                else:
                    st.sidebar.warning("Message cannot be empty.")
    else:
        st.sidebar.write("No escalated tickets available.")