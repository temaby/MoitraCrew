# Repository Context Report: inex

## 1. Tech Stack
*   **Backend Language:** C# (.NET 8.0)
*   **Backend Framework:** ASP.NET Core Web API
*   **Database & ORM:** MySQL (using `Pomelo.EntityFrameworkCore.MySql`), Entity Framework Core 8.0
*   **Frontend Language:** TypeScript
*   **Frontend Framework:** React (SPA)
*   **State Management:** Redux Toolkit (observed in `inex\ClientApp\src\store`)
*   **Key Libraries:**
    *   **Backend:** AutoMapper (for DTO mapping), Serilog (logging), Swashbuckle (Swagger/OpenAPI), CsvHelper, Polly (resilience).
    *   **Frontend:** React, Redux Toolkit, CSS Modules (`*.module.css`).

## 2. Project Structure Overview
*   **`inex/`**: The main Web API project.
    *   **`Controllers/`**: Contains API endpoints (e.g., `AccountsController`, `TransactionsController`).
    *   **`ClientApp/`**: The React frontend application.
        *   **`src/components/`**: Reusable UI components.
        *   **`src/pages/`**: View-level components (e.g., `Accounts.tsx`, `Transactions.tsx`).
        *   **`src/store/`**: Redux slices and actions.
        *   **`src/model/`**: TypeScript interfaces and types for the domain.
*   **`inex.Data/`**: Data access layer.
    *   **`Models/`**: Entity Framework entities (e.g., `Account`, `Transaction`).
    *   **`Configurations/`**: Fluent API configurations for database mapping.
    *   **`Repositories/`**: Repository pattern implementation and Unit of Work.
    *   **`Migrations/`**: Entity Framework database migrations.
*   **`inex.Services/`**: Business logic layer.
    *   **`Services/`**: Service implementations (e.g., `AccountService`, `TransactionService`).
    *   **`Models/Records/`**: Data Transfer Objects (DTOs) using C# `record` types.
    *   **`Models/ConfigProfiles/`**: AutoMapper mapping profiles.
*   **`inex.Services.Tests/`**: Unit tests for the service layer.

## 3. Existing Functionality: Accounts
The infrastructure for "Add accounts create/edit/delete functionality" is **already largely implemented** on the backend but may be missing or incomplete on the frontend.
*   **Backend Controller (`AccountsController.cs`):** Has `POST` (Add), `PUT` (Update), and `DELETE` (Delete/DeleteList) endpoints.
*   **Backend Service (`AccountService.cs`):** Implements `CreateAsync`, `UpdateAsync`, and `DeleteAsync`.
*   **Backend DTOs:** `AccountCreateDTO`, `AccountUpdateDTO`, and `AccountDetailsDTO` are defined.
*   **Frontend Page (`Accounts.tsx`):** Exists, but currently appears to focus on listing accounts. The task likely involves adding the UI forms (modals or separate views) to trigger these existing API endpoints.
*   **Frontend Store:** `accounts-slice.ts` and `accounts-actions.ts` handle state management for accounts.

## 4. Coding Conventions and Patterns
*   **Layered Architecture:** Clear separation between Controllers -> Services -> Repositories -> Data Models.
*   **DTO Pattern:** Services communicate with Controllers using DTOs (records), mapped from Entities using AutoMapper.
*   **Unit of Work / Repository Pattern:** Centralized data access via `IInExUnitOfWork`.
*   **Asynchronous Programming:** Extensive use of `async/await` throughout the stack.
*   **Naming Conventions:** Standard .NET PascalCase for methods/classes; CamelCase for private fields with underscore prefix (e.g., `_accountService`).
*   **Frontend Pattern:** Functional React components with hooks, Redux for global state, and TypeScript for type safety.

## 5. Recommended Test Command
*   **Backend Tests:** `dotnet test` (run from the root directory to execute tests in `inex.Services.Tests`).
*   **Frontend Tests:** `npm test` (run from within the `inex/ClientApp` directory).